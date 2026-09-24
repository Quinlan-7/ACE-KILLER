#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
硬件信息检测模块 v2.2
========================
用于检测显卡（AMD / NVIDIA / Intel）与内存容量信息，
供“游戏模式”与状态页展示，辅助 AMD 平台的针对性优化。
仅读取系统信息，不做任何修改。
"""

import ctypes
import ctypes.wintypes as wintypes
import os
import re
import time
import winreg
from typing import Dict, List

from loguru import logger

# 显示适配器设备类 GUID
_DISPLAY_CLASS_GUID = "{4d36e968-e325-11ce-bfc1-08002be10318}"

# 显卡信息缓存（避免状态页高频刷新时反复读取注册表）
_gpu_cache: List[Dict] = []
_gpu_cache_time: float = 0.0
_GPU_CACHE_TTL = 60.0  # 缓存 60 秒


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MEMORYSTATUSEX)]
_kernel32.GlobalMemoryStatusEx.restype = wintypes.BOOL


def get_gpu_list() -> List[Dict]:
    """返回显卡列表: [{"name": str, "vendor": str}, ...]（带 60 秒缓存）"""
    global _gpu_cache, _gpu_cache_time
    now = time.time()
    if _gpu_cache and (now - _gpu_cache_time) < _GPU_CACHE_TTL:
        return list(_gpu_cache)

    adapters: List[Dict] = []
    base = r"SYSTEM\CurrentControlSet\Control\Class\\" + _DISPLAY_CLASS_GUID
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base)
    except OSError:
        return adapters
    try:
        idx = 0
        while True:
            try:
                sub_name = winreg.EnumKey(key, idx)
                idx += 1
            except OSError:
                break
            if not sub_name.isdigit():
                continue
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base + "\\" + sub_name) as sub:
                    desc, _ = winreg.QueryValueEx(sub, "DriverDesc")
                    if not desc:
                        continue
                    vendor = _classify_vendor(desc)
                    adapters.append({"name": desc.strip(), "vendor": vendor})
            except OSError:
                continue
    finally:
        winreg.CloseKey(key)
    _gpu_cache = list(adapters)
    _gpu_cache_time = now
    return adapters


def _classify_vendor(name: str) -> str:
    upper = name.upper()
    if "AMD" in upper or "RADEON" in upper or "ATI" in upper:
        return "AMD"
    if "NVIDIA" in upper or "GEFORCE" in upper or "RTX" in upper or "GTX" in upper:
        return "NVIDIA"
    if "INTEL" in upper or "ARC" in upper or "HD GRAPHICS" in upper or "UHD" in upper:
        return "Intel"
    return "未知"


def get_gpu_summary() -> Dict:
    """汇总显卡信息"""
    gpus = get_gpu_list()
    vendors = set(g["vendor"] for g in gpus if g["vendor"] != "未知")
    return {
        "gpus": gpus,
        "has_amd": "AMD" in vendors,
        "has_nvidia": "NVIDIA" in vendors,
        "has_intel": "Intel" in vendors,
        "primary": gpus[0] if gpus else None,
    }


def get_memory_info() -> Dict:
    """内存信息（GB）"""
    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    try:
        if not _kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            raise OSError("GlobalMemoryStatusEx 调用失败")
        return {
            "total_gb": round(stat.ullTotalPhys / (1024 ** 3), 1),
            "available_gb": round(stat.ullAvailPhys / (1024 ** 3), 1),
            "usage_percent": int(stat.dwMemoryLoad),
        }
    except Exception as e:
        logger.debug(f"获取内存信息失败: {e}")
        return {"total_gb": 0.0, "available_gb": 0.0, "usage_percent": 0}


def get_hardware_summary() -> Dict:
    """完整硬件摘要"""
    return {
        "gpu": get_gpu_summary(),
        "memory": get_memory_info(),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_hardware_summary(), ensure_ascii=False, indent=2))
