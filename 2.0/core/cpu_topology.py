#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CPU 拓扑与厂商检测模块 v2.2
================================
通过 Windows API 获取处理器真实物理拓扑，为 AMD / Intel 混合架构提供
“效能核心”智能选择：

- AMD CPU（SMT）：全部核心同构，选择最后一个物理核心作为效能目标；
- Intel 混合架构（大小核）：优先选择 EfficiencyClass 最高的能效核；
- 传统方案：直接使用最后一个逻辑处理器作为回退。

模块内部使用标准 Windows API（GetLogicalProcessorInformationEx），
仅读取信息，不做任何内核级修改。
"""

import ctypes
import ctypes.wintypes as wintypes
import os
import re
import sys
import winreg
from typing import Dict, List, Optional, Tuple

from loguru import logger

# ---------------------------------------------------------------- 常量
LOGICAL_PROCESSOR_RELATION_PROCESSOR = 0
LOGICAL_PROCESSOR_RELATION_NUMA_NODE = 1
LOGICAL_PROCESSOR_RELATION_CACHE = 2
LOGICAL_PROCESSOR_RELATION_PROCESSOR_PACKAGE = 3
LOGICAL_PROCESSOR_RELATION_GROUP = 4
LOGICAL_PROCESSOR_RELATION_ALL = 0xFFFF

RelationProcessorCore = 0
RelationNumaNode = 1
RelationCache = 2
RelationProcessorPackage = 3
RelationGroup = 4
RelationProcessorDie = 5
RelationNumaNodeEx = 6
RelationProcessorModule = 7

_PTR = ctypes.sizeof(ctypes.c_size_t)  # 8 on x64, 4 on x86


class SYSTEM_LOGICAL_PROCESSOR_INFORMATION(ctypes.Structure):
    """经典拓扑结构（仅需头部字段，union 以占位字节表示）"""
    _fields_ = [
        ("ProcessorMask", ctypes.c_size_t),
        ("Relationship", ctypes.c_ubyte),
        ("_pad", ctypes.c_ubyte * (_PTR - 1)),
        ("_union", ctypes.c_ubyte * 8),
    ]


class GROUP_AFFINITY(ctypes.Structure):
    _fields_ = [
        ("Mask", ctypes.c_size_t),
        ("Group", ctypes.c_ushort),
        ("_reserved", ctypes.c_ushort * 3),
    ]


class SLPIEX_HEADER(ctypes.Structure):
    """SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX 头部"""
    _fields_ = [
        ("Relationship", ctypes.c_ulong),
        ("Size", ctypes.c_ulong),
    ]


_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.GetLogicalProcessorInformation.argtypes = [
    ctypes.POINTER(SYSTEM_LOGICAL_PROCESSOR_INFORMATION),
    ctypes.POINTER(wintypes.DWORD),
]
_kernel32.GetLogicalProcessorInformation.restype = wintypes.BOOL
_kernel32.GetLogicalProcessorInformationEx.argtypes = [
    wintypes.ULONG,
    ctypes.c_void_p,
    ctypes.POINTER(wintypes.DWORD),
]
_kernel32.GetLogicalProcessorInformationEx.restype = wintypes.BOOL

# ---------------------------------------------------------------- 缓存
_cache: Dict[str, object] = {}


def _get_registry_cpu_info() -> Dict[str, str]:
    """从注册表读取 CPU 品牌与厂商标识"""
    info = {"brand": "", "vendor": ""}
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        )
        try:
            brand, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            info["brand"] = brand.strip() if brand else ""
        except OSError:
            pass
        try:
            vendor, _ = winreg.QueryValueEx(key, "VendorIdentifier")
            info["vendor"] = vendor.strip() if vendor else ""
        except OSError:
            pass
        winreg.CloseKey(key)
    except OSError:
        pass
    return info


def _get_logical_processor_info() -> Optional[List[Tuple[int, int]]]:
    """
    经典 API：返回 [(ProcessorMask, Relationship), ...]
    Relationship == RelationProcessorCore(0) 的条目代表一个物理核心。
    """
    length = wintypes.DWORD(0)
    _kernel32.GetLogicalProcessorInformation(None, ctypes.byref(length))
    err = ctypes.get_last_error()
    if length.value == 0:
        return None
    buf = (ctypes.c_ubyte * length.value)()
    if not _kernel32.GetLogicalProcessorInformation(
        ctypes.cast(buf, ctypes.POINTER(SYSTEM_LOGICAL_PROCESSOR_INFORMATION)),
        ctypes.byref(length),
    ):
        return None
    stride = ctypes.sizeof(SYSTEM_LOGICAL_PROCESSOR_INFORMATION)
    entries = []
    count = length.value // stride
    for i in range(count):
        entry = ctypes.cast(
            ctypes.byref(buf, i * stride),
            ctypes.POINTER(SYSTEM_LOGICAL_PROCESSOR_INFORMATION),
        ).contents
        entries.append((entry.ProcessorMask, entry.Relationship))
    return entries


def _get_logical_processor_info_ex() -> Optional[List[Dict]]:
    """
    Ex 版 API：返回核心关系列表
    [{"efficiency_class": int, "logical_ids": [int, ...]}, ...]
    """
    results = []
    for rel in (RelationProcessorCore,):
        length = wintypes.DWORD(0)
        _kernel32.GetLogicalProcessorInformationEx(rel, None, ctypes.byref(length))
        if length.value == 0:
            return None
        buf = (ctypes.c_ubyte * length.value)()
        if not _kernel32.GetLogicalProcessorInformationEx(
            rel, ctypes.cast(buf, ctypes.c_void_p), ctypes.byref(length)
        ):
            return None
        offset = 0
        while offset < length.value:
            header = ctypes.cast(
                ctypes.byref(buf, offset),
                ctypes.POINTER(SLPIEX_HEADER),
            ).contents
            size = header.Size
            if size <= 0:
                break
            # PROCESSOR_RELATIONSHIP 布局:
            # offset0: BYTE Flags; offset1: BYTE EfficiencyClass;
            # offset2..21: BYTE Reserved[20]; offset22: USHORT GroupCount;
            # offset24: GROUP_AFFINITY GroupMask[...]
            data_ptr = offset + 8  # header 之后
            eff_class = buf[data_ptr + 1] if (data_ptr + 1) < length.value else 0
            if (data_ptr + 22 + 2) <= length.value:
                group_count = int.from_bytes(
                    bytes(buf[data_ptr + 22: data_ptr + 24]), "little"
                )
            else:
                group_count = 1
            logical_ids = []
            for g in range(max(1, group_count)):
                base = data_ptr + 24 + g * 16
                if base + 8 > length.value:
                    break
                mask = int.from_bytes(bytes(buf[base: base + 8]), "little")
                for bit in range(64):
                    if mask & (1 << bit):
                        logical_ids.append(bit)
            results.append({
                "efficiency_class": eff_class,
                "logical_ids": logical_ids,
            })
            offset += size
    return results or None


def _logical_to_physical_mapping() -> Tuple[Optional[Dict[int, int]], List[int]]:
    """
    返回 (logical_id -> physical_core_index, core_masks)
    优先使用 Ex API（条目自带 Size 字段，解析可靠），
    其次经典 API，最后回退到相邻配对假设。
    """
    mapping: Dict[int, int] = {}
    core_masks: List[int] = []

    # 方式1: Ex API（最可靠）
    ex = _get_logical_processor_info_ex()
    if ex:
        for core_idx, item in enumerate(ex):
            ids = item.get("logical_ids", [])
            if not ids:
                continue
            mask = 0
            for lid in ids:
                mapping[lid] = core_idx
                mask |= (1 << lid)
            core_masks.append(mask)
        if core_masks:
            return mapping, core_masks

    # 方式2: 经典 API
    entries = _get_logical_processor_info()
    if entries:
        core_idx = 0
        for mask, rel in entries:
            if rel == RelationProcessorCore:
                core_masks.append(mask)
                for bit in range(64):
                    if mask & (1 << bit):
                        mapping[bit] = core_idx
                core_idx += 1
        if core_masks:
            # 合理性校验：物理核心数不可能超过逻辑处理器数，防止结构体错位产生垃圾数据
            try:
                import psutil
                logical_count = psutil.cpu_count(logical=True) or 0
            except Exception:
                logical_count = 0
            if logical_count and len(core_masks) > logical_count:
                logger.warning(
                    f"经典 API 解析异常（物理核 {len(core_masks)} > 逻辑核 {logical_count}），"
                    "改用相邻配对假设"
                )
                core_masks = []
                mapping = {}
            else:
                return mapping, core_masks

    # 方式3: 相邻配对假设（SMT 线程成对排列）
    try:
        import psutil
        logical = psutil.cpu_count(logical=True) or 0
        physical = psutil.cpu_count(logical=False) or 0
    except Exception:
        logical = 0
        physical = 0
    if logical and physical and logical >= physical:
        threads_per_core = logical // physical
        for c in range(physical):
            mask = 0
            for t in range(threads_per_core):
                lid = c * threads_per_core + t
                mapping[lid] = c
                mask |= (1 << lid)
            core_masks.append(mask)
        return mapping, core_masks
    return None, []


def get_cpu_brand() -> str:
    """CPU 品牌字符串，如 'AMD Ryzen 7 5800X 8-Core Processor'"""
    if "brand" not in _cache:
        info = _get_registry_cpu_info()
        _cache["brand"] = info.get("brand", "")
    return _cache["brand"]


def get_cpu_vendor() -> str:
    """返回 'AMD' / 'Intel' / '未知'"""
    if "vendor" not in _cache:
        info = _get_registry_cpu_info()
        vendor_raw = info.get("vendor", "")
        if "AuthenticAMD" in vendor_raw:
            vendor = "AMD"
        elif "GenuineIntel" in vendor_raw:
            vendor = "Intel"
        elif "AMD" in vendor_raw.upper() or "RYZEN" in vendor_raw.upper():
            vendor = "AMD"
        elif "INTEL" in vendor_raw.upper():
            vendor = "Intel"
        else:
            vendor = "未知"
        _cache["vendor"] = vendor
    return _cache["vendor"]


def is_amd_cpu() -> bool:
    return get_cpu_vendor() == "AMD"


def is_intel_cpu() -> bool:
    return get_cpu_vendor() == "Intel"


def get_core_counts() -> Tuple[int, int]:
    """返回 (物理核心数, 逻辑处理器数)"""
    if "core_counts" not in _cache:
        mapping, core_masks = _logical_to_physical_mapping()
        physical = len(core_masks) if core_masks else 0
        logical = len(mapping) if mapping else 0
        try:
            import psutil
            if logical == 0:
                logical = psutil.cpu_count(logical=True) or 0
            if physical == 0:
                physical = psutil.cpu_count(logical=False) or 0
        except Exception:
            pass
        _cache["core_counts"] = (physical, logical)
    return _cache["core_counts"]


def _get_efficiency_classes() -> List[Dict]:
    """Ex API 返回的 (efficiency_class, logical_ids) 列表，失败返回 None"""
    if "efficiency_classes" not in _cache:
        _cache["efficiency_classes"] = _get_logical_processor_info_ex()
    return _cache["efficiency_classes"]


def get_eco_target_cpus() -> List[int]:
    """
    返回适合承载后台低优先级进程的“效能核心”逻辑 CPU 列表。

    优先级：
    1. Intel 混合架构：取 EfficiencyClass 最大的核心（能效核）；
    2. AMD / 同构架构：取最后一个物理核心（SMT 下取该核心的第一个线程）；
    3. 回退：最后一个逻辑处理器。
    """
    if "eco_target" in _cache:
        return _cache["eco_target"]

    target: List[int] = []

    # Intel 混合架构：优先能效核
    ex = _get_efficiency_classes()
    if ex:
        max_class = max(item["efficiency_class"] for item in ex)
        if max_class > 0:
            eff_cores = [
                item for item in ex if item["efficiency_class"] == max_class
            ]
            if eff_cores:
                last = eff_cores[-1]
                ids = sorted(last.get("logical_ids", []))
                target = [ids[0]] if ids else []
                _cache["eco_target"] = target
                return target

    # AMD / 同构：最后一个物理核心
    mapping, core_masks = _logical_to_physical_mapping()
    if core_masks:
        last_mask = core_masks[-1]
        ids = []
        for bit in range(64):
            if last_mask & (1 << bit):
                ids.append(bit)
        if ids:
            # SMT 下取第一个线程，最大限度让出同核心的另一线程
            target = [min(ids)]
            _cache["eco_target"] = target
            return target

    # 回退：最后一个逻辑处理器
    try:
        import psutil
        total = psutil.cpu_count(logical=True) or 0
    except Exception:
        total = 0
    if total > 0:
        target = [total - 1]

    _cache["eco_target"] = target
    return target


def get_eco_affinity_mask() -> Optional[int]:
    """返回效能核心的亲和性掩码（供 SetProcessAffinityMask 使用）"""
    target = get_eco_target_cpus()
    if not target:
        return None
    mask = 0
    for lid in target:
        mask |= (1 << lid)
    return mask


def get_cpu_summary() -> Dict:
    """汇总 CPU 信息，供 UI 展示"""
    physical, logical = get_core_counts()
    return {
        "brand": get_cpu_brand(),
        "vendor": get_cpu_vendor(),
        "physical_cores": physical,
        "logical_processors": logical,
        "eco_target": get_eco_target_cpus(),
        "is_amd": is_amd_cpu(),
        "is_intel": is_intel_cpu(),
    }


if __name__ == "__main__":
    summary = get_cpu_summary()
    print(summary)
