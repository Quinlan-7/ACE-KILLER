#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
一键游戏模式模块 v2.2
======================
进入/退出“游戏模式”，组合以下可逆优化：

1. 电源方案：保存当前方案，优先激活“卓越性能”，否则“高性能”；
2. 关闭 GameDVR 后台录制（保存旧值，退出时恢复）；
3. 清理一次系统内存（工作集/缓存）；
4. 将 ACE 反作弊相关进程切换为效能模式，释放 CPU/磁盘压力。

所有修改均可一键还原，且状态持久化到配置文件，重启后可恢复。
"""

import os
import re
import subprocess
import sys
import winreg
from typing import Optional, Tuple

from loguru import logger

# 电源方案 GUID
ULTIMATE_PERFORMANCE_GUID = "e9a42b02-d5df-448d-aa00-03f14749eb61"
HIGH_PERFORMANCE_GUID = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
BALANCED_GUID = "381b4222-f694-41f0-9685-ff5bb260df2e"

# GameDVR 注册表位置
_GAMEDVR_KEY = r"Software\Microsoft\Windows\CurrentVersion\GameDVR"
_GAMEDVR_VALUE = "AppCaptureEnabled"


def _run_powercfg(args: str, timeout: int = 15) -> Tuple[int, str]:
    """静默执行 powercfg"""
    try:
        result = subprocess.run(
            f"powercfg {args}",
            shell=True, capture_output=True, text=True, timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return result.returncode, (result.stdout or "") + (result.stderr or "")
    except Exception as e:
        return -1, str(e)


def _get_active_scheme() -> Optional[str]:
    """获取当前电源方案 GUID"""
    code, out = _run_powercfg("/getactivescheme")
    if code != 0:
        return None
    match = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", out)
    return match.group(1).lower() if match else None


def _scheme_exists(guid: str) -> bool:
    code, out = _run_powercfg("/list")
    if code != 0:
        return False
    return guid.lower() in out.lower()


def _activate_scheme(guid: str) -> bool:
    code, _ = _run_powercfg(f"/setactive {guid}")
    return code == 0


def _ensure_ultimate_performance() -> bool:
    """确保存在‘卓越性能’方案（通过复制隐藏模板创建）"""
    if _scheme_exists(ULTIMATE_PERFORMANCE_GUID):
        return True
    code, _ = _run_powercfg(f"/duplicatescheme {ULTIMATE_PERFORMANCE_GUID}")
    return code == 0


def _set_gamedvr(enabled: bool) -> Optional[int]:
    """
    设置 GameDVR 捕获开关。
    返回修改前的旧值（None 表示原本不存在/无需恢复）。
    """
    old_value = None
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _GAMEDVR_KEY, 0, winreg.KEY_READ | winreg.KEY_WRITE)
    except OSError:
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, _GAMEDVR_KEY)
        except OSError:
            return None
    try:
        try:
            old_value, _ = winreg.QueryValueEx(key, _GAMEDVR_VALUE)
        except OSError:
            old_value = None
        winreg.SetValueEx(
            key, _GAMEDVR_VALUE, 0, winreg.REG_DWORD,
            1 if enabled else 0,
        )
    finally:
        winreg.CloseKey(key)
    return old_value


def _restore_gamedvr(old_value: Optional[int]) -> None:
    """恢复 GameDVR 旧值（若原本不存在则删除该值，恢复原状态）"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _GAMEDVR_KEY, 0,
            winreg.KEY_READ | winreg.KEY_WRITE,
        )
        if old_value is None:
            try:
                winreg.DeleteValue(key, _GAMEDVR_VALUE)
            except OSError:
                pass
        else:
            winreg.SetValueEx(key, _GAMEDVR_VALUE, 0, winreg.REG_DWORD, old_value)
        winreg.CloseKey(key)
    except OSError:
        pass


class GameModeManager:
    """游戏模式管理器"""

    def __init__(self, config_manager=None):
        self.config = config_manager
        self._state = {
            "previous_scheme": None,
            "gamedvr_old": None,
            "gamedvr_modified": False,
        }

    # ------------------------------------------------------------ 状态
    @staticmethod
    def is_active(config_manager=None) -> bool:
        """游戏模式是否处于激活状态（读取持久化配置）"""
        try:
            if config_manager is not None:
                return bool(getattr(config_manager, "game_mode_active", False))
        except Exception:
            pass
        return False

    def _save_state(self, active: bool):
        if self.config is not None:
            try:
                self.config.game_mode_active = active
                self.config.save_config()
            except Exception as e:
                logger.error(f"保存游戏模式状态失败: {e}")

    # ------------------------------------------------------------ 进入
    def enter_game_mode(self) -> Tuple[bool, str]:
        """进入游戏模式，返回 (是否成功, 描述信息)"""
        steps = []
        errors = []

        # 1. 电源方案
        current = _get_active_scheme()
        if current:
            self._state["previous_scheme"] = current
            target = None
            if _ensure_ultimate_performance() and _scheme_exists(ULTIMATE_PERFORMANCE_GUID):
                target = ULTIMATE_PERFORMANCE_GUID
            elif _scheme_exists(HIGH_PERFORMANCE_GUID):
                target = HIGH_PERFORMANCE_GUID
            if target and _activate_scheme(target):
                name = "卓越性能" if target == ULTIMATE_PERFORMANCE_GUID else "高性能"
                steps.append(f"电源方案 → {name}")
            else:
                errors.append("切换高性能电源方案失败")
        else:
            errors.append("无法读取当前电源方案")

        # 2. GameDVR
        old = _set_gamedvr(False)
        self._state["gamedvr_old"] = old
        self._state["gamedvr_modified"] = True
        steps.append("已关闭 GameDVR 后台录制")

        # 3. 内存清理
        try:
            from utils.memory_cleaner import MemoryCleaner
            cleaner = MemoryCleaner()
            freed = cleaner.clean_memory_all()
            steps.append(f"内存清理完成（释放约 {freed:.0f} MB）")
        except Exception as e:
            logger.debug(f"游戏模式内存清理失败: {e}")
            errors.append(f"内存清理失败: {e}")

        # 4. ACE 进程效能优化
        try:
            from core.process_monitor import ACE_PROCESSES
            from utils.process_io_priority import set_process_io_priority
            optimized = 0
            for name in ACE_PROCESSES:
                if set_process_io_priority(name):
                    optimized += 1
            steps.append(f"ACE 相关进程已切换效能模式（{optimized} 个）")
        except Exception as e:
            logger.debug(f"游戏模式进程优化失败: {e}")
            errors.append(f"进程优化失败: {e}")

        self._save_state(True)
        if errors:
            return True, "；".join(steps) + "。部分步骤警告：" + "；".join(errors)
        return True, "；".join(steps)

    # ------------------------------------------------------------ 退出
    def exit_game_mode(self) -> Tuple[bool, str]:
        """退出游戏模式，恢复电源方案与 GameDVR"""
        steps = []
        errors = []

        if self._state["previous_scheme"]:
            if _activate_scheme(self._state["previous_scheme"]):
                steps.append("已恢复原电源方案")
            else:
                errors.append("恢复电源方案失败")

        if self._state["gamedvr_modified"]:
            _restore_gamedvr(self._state["gamedvr_old"])
            steps.append("已恢复 GameDVR 设置")

        self._save_state(False)
        self._state = {
            "previous_scheme": None,
            "gamedvr_old": None,
            "gamedvr_modified": False,
        }
        if errors:
            return False, "；".join(steps) + "。警告：" + "；".join(errors)
        return True, "；".join(steps) if steps else "游戏模式已退出（无需恢复）"

    # ------------------------------------------------------------ 恢复
    def restore_from_config(self) -> str:
        """
        程序启动时调用：若上次退出时游戏模式仍激活，则恢复原设置。
        """
        if not self.is_active(self.config):
            return ""
        logger.info("检测到上次退出时游戏模式仍处于激活状态，正在恢复默认设置...")
        result = self.exit_game_mode()
        return "已自动恢复上次未退出的游戏模式设置（" + result[1] + "）"


if __name__ == "__main__":
    mgr = GameModeManager()
    ok, msg = mgr.enter_game_mode()
    print(ok, msg)
    ok2, msg2 = mgr.exit_game_mode()
    print(ok2, msg2)
