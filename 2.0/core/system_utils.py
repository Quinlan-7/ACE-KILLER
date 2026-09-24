#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
系统工具函数模块 v2.2
"""

import ctypes
import os
import sys
from utils.logger import logger

# 单实例互斥体句柄（保持引用，避免句柄被回收导致互斥体提前销毁）
_MUTEX_HANDLE = None


def run_as_admin():
    """
    判断是否以管理员权限运行，如果不是则尝试获取管理员权限

    Returns:
        bool: 是否以管理员权限运行
    """
    if not ctypes.windll.shell32.IsUserAnAdmin():
        # 将参数逐项引号包裹，避免路径/参数含空格时被拆分
        args = " ".join(
            '"%s"' % a if " " in a else a for a in sys.argv[1:]
        )
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, args, None, 1
        )
        return False
    return True


def check_single_instance():
    """
    检查程序是否已经在运行，确保只有一个实例

    Returns:
        bool: 如果是首次运行返回True，否则返回False
    """
    global _MUTEX_HANDLE
    _MUTEX_HANDLE = ctypes.windll.kernel32.CreateMutexW(
        None, False, "Global\\ACE-KILLER_MUTEX"
    )
    if ctypes.windll.kernel32.GetLastError() == 183:
        logger.warning("程序已经在运行中，无法启动多个实例！")
        show_already_running_dialog()
        return False
    return True


def show_already_running_dialog():
    """
    显示程序已运行的提醒对话框
    """
    try:
        message = (
            "ACE-KILLER 已经在运行中！\n\n"
            "程序只允许运行一个实例。\n"
            "请检查系统托盘是否有ACE-KILLER图标。\n\n"
            "如果找不到运行中的程序，请尝试：\n"
            "• 检查任务管理器中是否有ACE-KILLER进程\n"
            "• 重启电脑后再次运行程序"
        )

        title = "ACE-KILLER - 程序已运行"

        # 使用Windows API显示消息框
        # MB_OK = 0x00000000, MB_ICONINFORMATION = 0x00000040, MB_TOPMOST = 0x00040000
        ctypes.windll.user32.MessageBoxW(
            0,
            message,
            title,
            0x00000040 | 0x00040000
        )

        logger.debug("已显示程序重复运行提醒对话框")

    except Exception as e:
        logger.error(f"显示程序重复运行对话框失败: {str(e)}")
        print("ACE-KILLER 已经在运行中，无法启动多个实例！")


def get_program_path():
    """
    获取程序完整路径

    Returns:
        str: 程序完整路径
    """
    if getattr(sys, 'frozen', False):
        return sys.executable
    else:
        return os.path.abspath(sys.argv[0])


# ----------------------------------------------------------------
# 开机自启动（委托给 core.autostart 双通道模块）
# ----------------------------------------------------------------
def check_auto_start(app_name="ACE-KILLER", force=None):
    """
    检查是否设置了开机自启（快捷方式 + 计划任务）

    Args:
        app_name (str): 应用名称
        force (bool): None 表示同时检查两种方式

    Returns:
        bool: 是否设置了开机自启
    """
    from core.autostart import check_auto_start as _check
    if force is None:
        force = True
    return _check(app_name, force=force)


def enable_auto_start(app_name="ACE-KILLER", delay_seconds=0, force=None):
    """
    设置开机自启（快捷方式；强制模式下同时创建最高权限计划任务）

    Args:
        app_name (str): 应用名称
        delay_seconds (int): 延迟启动秒数，0 表示不延迟
        force (bool): 强制模式，None 表示使用默认（强制）

    Returns:
        bool: 操作是否成功
    """
    from core.autostart import enable_auto_start as _enable
    if force is None:
        force = True
    return _enable(app_name, delay_seconds, force=force)


def disable_auto_start(app_name="ACE-KILLER", force=None):
    """
    取消开机自启（删除快捷方式；强制模式下同时删除计划任务）

    Args:
        app_name (str): 应用名称
        force (bool): 强制模式

    Returns:
        bool: 操作是否成功
    """
    from core.autostart import disable_auto_start as _disable
    if force is None:
        force = True
    return _disable(app_name, force=force)
