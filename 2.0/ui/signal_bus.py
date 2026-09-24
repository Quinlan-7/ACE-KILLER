#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
全局信号总线 v2.0
基于 PySide6 QObject + Signal 的中心事件系统
"""

from PySide6.QtCore import QObject, Signal


class SignalBus(QObject):
    """全局信号总线 - 单例

    v2.2.1: 移除 __new__ 单例实现。
    原实现中第二次调用 SignalBus() 时，Python 会对 __new__ 返回的
    已有实例再次调用 QObject.__init__，触发 shiboken
    "You can't initialize a QObject object twice" 崩溃（源码/打包环境均复现）。
    改用模块级实例 + 工厂函数持有，构造只发生一次。
    """

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


# v2.2.1: 模块级单例实例（由 get_signal_bus 工厂持有）
_instance = None


def get_signal_bus() -> SignalBus:
    """获取信号总线单例（只构造一次，返回同一实例）"""
    global _instance
    if _instance is None:
        _instance = SignalBus()
    return _instance
