#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Windows API 共享常量与结构体 v2.1
整合分散在各模块中的重复定义，统一引用入口
"""

import ctypes
from ctypes import wintypes


# =============================================================================
# 进程访问权限
# =============================================================================

PROCESS_ALL_ACCESS = 0x1F0FFF
PROCESS_SET_INFORMATION = 0x0200
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
PROCESS_TERMINATE = 0x0001

# =============================================================================
# 内存操作常量
# =============================================================================

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000
PAGE_READWRITE = 0x04

# 系统信息类别
SystemFileCacheInformation = 0x15
SystemMemoryListInformation = 0x50
SystemCombinePhysicalMemoryInformation = 0x82

# 内存列表命令
MemoryEmptyWorkingSets = 0x2
MemoryFlushModifiedList = 0x3
MemoryPurgeStandbyList = 0x4
MemoryPurgeLowPriorityStandbyList = 0x5

# =============================================================================
# 进程优先级类 (win32process)
# =============================================================================

IDLE_PRIORITY_CLASS = 0x40
BELOW_NORMAL_PRIORITY_CLASS = 0x4000
NORMAL_PRIORITY_CLASS = 0x20
ABOVE_NORMAL_PRIORITY_CLASS = 0x8000
HIGH_PRIORITY_CLASS = 0x80
REALTIME_PRIORITY_CLASS = 0x100

# =============================================================================
# 进程效能模式 (Power Throttling)
# =============================================================================

PROCESS_POWER_THROTTLING_INFORMATION = 4
PROCESS_POWER_THROTTLING_EXECUTION_SPEED = 0x1
POWER_THROTTLING_PROCESS_ENABLE = 0x1
POWER_THROTTLING_PROCESS_DISABLE = 0x2


class PROCESS_POWER_THROTTLING_STATE(ctypes.Structure):
    """进程功耗节流状态结构体"""
    _fields_ = [
        ("Version", wintypes.DWORD),
        ("ControlMask", wintypes.DWORD),
        ("StateMask", wintypes.DWORD),
    ]


# =============================================================================
# I/O 优先级
# =============================================================================

ProcessIoPriority = 33


class IO_PRIORITY_HINT:
    """I/O 优先级枚举"""
    IoPriorityVeryLow = 0
    IoPriorityLow = 1
    IoPriorityNormal = 2
    IoPriorityCritical = 3


# =============================================================================
# 系统文件缓存信息结构
# =============================================================================

class SYSTEM_FILECACHE_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("CurrentSize", ctypes.c_size_t),
        ("PeakSize", ctypes.c_size_t),
        ("PageFaultCount", wintypes.ULONG),
        ("MinimumWorkingSet", ctypes.c_size_t),
        ("MaximumWorkingSet", ctypes.c_size_t),
        ("CurrentSizeIncludingTransitionInPages", ctypes.c_size_t),
        ("PeakSizeIncludingTransitionInPages", ctypes.c_size_t),
        ("TransitionRePurposeCount", wintypes.ULONG),
        ("Flags", wintypes.ULONG),
    ]


class MEMORY_COMBINE_INFORMATION_EX(ctypes.Structure):
    _fields_ = [
        ("Handle", wintypes.HANDLE),
        ("PagesCombined", ctypes.c_ulonglong),
        ("Flags", wintypes.ULONG),
    ]
