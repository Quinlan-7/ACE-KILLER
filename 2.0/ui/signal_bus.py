#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
全局信号总线 v2.0
基于 PySide6 QObject + Signal 的中心事件系统
"""

from PySide6.QtCore import QObject, Signal


class SignalBus(QObject):
    """全局信号总线 - 单例"""

    _instance = None

    # 进程相关信号
    process_limited = Signal(str)  # "pid:name:method"
    rule_applied = Signal(str)  # "rule_name:process_name:action"

    # Profile 相关信号
    profile_activated = Signal(str)  # profile_name
    profile_deactivated = Signal()

    # RAM 盘相关信号
    ramdisk_status_changed = Signal(bool)  # True=running, False=stopped

    # 内存清理相关信号
    memory_cleaned = Signal(int)  # freed_mb

    # 磁盘统计信号
    disk_stats_updated = Signal(object)  # dict

    # 通知信号
    notification_requested = Signal(str, str)  # title, message

    # 主题信号
    theme_changed = Signal(str)  # "light" | "dark"

    # 托盘状态信号
    tray_status_changed = Signal(str)  # "running"|"limited"|"idle"|"error"

    # 配置变更信号
    config_changed = Signal(str)  # section_name

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


def get_signal_bus() -> SignalBus:
    """获取信号总线单例"""
    return SignalBus()
