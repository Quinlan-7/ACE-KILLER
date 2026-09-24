#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
开机自启动管理模块 v2.2
========================
提供双通道自启动方案：

1. 启动文件夹快捷方式（传统方式）
2. 计划任务（/rl highest 最高权限，登录即启动）

“强制模式”下同时启用两种方式，即使启动文件夹被清理，
计划任务仍能保证程序随登录自动运行并以管理员权限启动。
"""

import os
import subprocess
import sys

from loguru import logger


def _get_startup_folder() -> str:
    return os.path.join(
        os.path.expanduser("~"),
        "AppData", "Roaming", "Microsoft", "Windows",
        "Start Menu", "Programs", "Startup",
    )


def _get_shortcut_path(app_name: str) -> str:
    return os.path.join(_get_startup_folder(), f"{app_name}.lnk")


def get_program_path() -> str:
    """获取程序完整路径（兼容源码运行与打包运行）"""
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(sys.argv[0])


def _build_arguments(delay_seconds: int = 0) -> str:
    args = "--minimized"
    if delay_seconds > 0:
        args += f" --delay {delay_seconds}"
    return args


# ---------------------------------------------------------------- 快捷方式
def enable_shortcut(app_name: str = "ACE-KILLER", delay_seconds: int = 0) -> bool:
    """在启动文件夹创建快捷方式"""
    try:
        import win32com.client
        startup_folder = _get_startup_folder()
        if not os.path.exists(startup_folder):
            os.makedirs(startup_folder, exist_ok=True)

        shortcut_path = _get_shortcut_path(app_name)
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.TargetPath = get_program_path()
        shortcut.Arguments = _build_arguments(delay_seconds)
        shortcut.Description = app_name
        shortcut.WorkingDirectory = os.path.dirname(get_program_path())
        shortcut.save()
        logger.debug(f"已创建启动快捷方式: {shortcut_path}")
        return True
    except Exception as e:
        logger.error(f"创建启动快捷方式失败: {e}")
        return False


def disable_shortcut(app_name: str = "ACE-KILLER") -> bool:
    """删除启动文件夹快捷方式"""
    try:
        shortcut_path = _get_shortcut_path(app_name)
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)
            logger.debug(f"已删除启动快捷方式: {shortcut_path}")
        return True
    except Exception as e:
        logger.error(f"删除启动快捷方式失败: {e}")
        return False


def check_shortcut(app_name: str = "ACE-KILLER") -> bool:
    """检查快捷方式是否存在且指向当前程序"""
    try:
        shortcut_path = _get_shortcut_path(app_name)
        if not os.path.exists(shortcut_path):
            return False
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        current_path = get_program_path()
        if shortcut.TargetPath.lower() != current_path.lower():
            logger.warning(f"启动快捷方式指向目标不一致: {shortcut.TargetPath}")
            return False
        # 参数以 --minimized 开头即视为有效（兼容带延迟启动）
        if not shortcut.Arguments.strip().startswith("--minimized"):
            logger.warning(f"启动快捷方式参数异常: {shortcut.Arguments}")
            return False
        return True
    except Exception as e:
        logger.error(f"检查启动快捷方式失败: {e}")
        return False


# ---------------------------------------------------------------- 计划任务
def _task_name(app_name: str = "ACE-KILLER") -> str:
    return f"{app_name}-AutoStart"


def _run_schtasks(cmd: str) -> "subprocess.CompletedProcess":
    """执行 schtasks 并安全解码输出（v2.2.1: 修复 GBK 输出导致解码崩溃）"""
    raw = subprocess.run(
        cmd, shell=True, capture_output=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    # 用 bytes 捕获，手动解码（errors=replace 兜底，任意编码都不崩溃）
    stdout = raw.stdout.decode("utf-8", errors="replace") if raw.stdout else ""
    stderr = raw.stderr.decode("utf-8", errors="replace") if raw.stderr else ""
    return type("CP", (), {"returncode": raw.returncode, "stdout": stdout, "stderr": stderr})


def enable_task(app_name: str = "ACE-KILLER", delay_seconds: int = 0) -> bool:
    """创建计划任务：登录时以最高权限启动"""
    try:
        exe = get_program_path()
        args = _build_arguments(delay_seconds)
        quoted = f'"{exe}" {args}'
        cmd = (
            f'schtasks /create /tn "{_task_name(app_name)}" /tr "{quoted}" '
            f'/sc onlogon /rl highest /f'
        )
        result = _run_schtasks(cmd)
        if result.returncode == 0:
            logger.debug(f"已创建计划任务 {_task_name(app_name)}")
            return True
        logger.error(f"创建计划任务失败: {result.stderr.strip() or result.stdout.strip()}")
        return False
    except Exception as e:
        logger.error(f"创建计划任务异常: {e}")
        return False


def disable_task(app_name: str = "ACE-KILLER") -> bool:
    """删除计划任务"""
    try:
        cmd = f'schtasks /delete /tn "{_task_name(app_name)}" /f'
        result = _run_schtasks(cmd)
        if result.returncode == 0:
            logger.debug(f"已删除计划任务 {_task_name(app_name)}")
            return True
        # 任务不存在也视为成功
        out = (result.stderr or result.stdout or "").lower()
        if "not found" in out or "不存在" in out:
            return True
        logger.error(f"删除计划任务失败: {result.stderr.strip() or result.stdout.strip()}")
        return False
    except Exception as e:
        logger.error(f"删除计划任务异常: {e}")
        return False


def check_task(app_name: str = "ACE-KILLER") -> bool:
    """检查计划任务是否存在"""
    try:
        cmd = f'schtasks /query /tn "{_task_name(app_name)}"'
        result = _run_schtasks(cmd)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"查询计划任务失败: {e}")
        return False


# ---------------------------------------------------------------- 统一入口
def enable_auto_start(
    app_name: str = "ACE-KILLER",
    delay_seconds: int = 0,
    force: bool = True,
) -> bool:
    """
    启用开机自启动。

    Args:
        app_name: 应用名
        delay_seconds: 延迟启动秒数
        force: 强制模式 —— 同时启用启动快捷方式与计划任务（最高权限）
    """
    ok_shortcut = enable_shortcut(app_name, delay_seconds)
    if not force:
        return ok_shortcut
    ok_task = enable_task(app_name, delay_seconds)
    return ok_shortcut and ok_task


def disable_auto_start(app_name: str = "ACE-KILLER", force: bool = True) -> bool:
    """取消开机自启动"""
    ok_shortcut = disable_shortcut(app_name)
    if not force:
        return ok_shortcut
    ok_task = disable_task(app_name)
    return ok_shortcut and ok_task


def check_auto_start(app_name: str = "ACE-KILLER", force: bool = True) -> bool:
    """检查开机自启动是否已生效"""
    if not force:
        return check_shortcut(app_name)
    return check_shortcut(app_name) or check_task(app_name)


if __name__ == "__main__":
    print("shortcut:", check_shortcut())
    print("task:", check_task())
    print("auto_start:", check_auto_start())
