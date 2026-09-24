#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
游戏模式模块单元测试 v2.2
（仅测试解析与状态逻辑，不实际修改电源方案 / 注册表）
"""

import os
import re
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.game_mode import (
    GameModeManager,
    _get_active_scheme,
    _scheme_exists,
    ULTIMATE_PERFORMANCE_GUID,
    HIGH_PERFORMANCE_GUID,
)


class _FakeConfig:
    """模拟 ConfigManager，不触碰真实配置文件"""

    game_mode_active = False

    def __init__(self):
        self.saved = False

    def save_config(self):
        self.saved = True
        return True


class TestGameModeParsing(unittest.TestCase):

    def test_active_scheme_regex(self):
        # 模拟 powercfg /getactivescheme 输出
        out = (
            "电源方案 GUID: 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c  "
            "(高性能)\r\n"
        )
        with mock.patch(
            "core.game_mode._run_powercfg",
            return_value=(0, out),
        ):
            self.assertEqual(
                _get_active_scheme(),
                HIGH_PERFORMANCE_GUID,
            )

    def test_active_scheme_none_on_error(self):
        with mock.patch(
            "core.game_mode._run_powercfg",
            return_value=(1, "error"),
        ):
            self.assertIsNone(_get_active_scheme())

    def test_scheme_exists(self):
        out = (
            "电源方案 GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (平衡) *\n"
            "电源方案 GUID: 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c  (高性能)\n"
        )
        with mock.patch(
            "core.game_mode._run_powercfg",
            return_value=(0, out),
        ):
            self.assertTrue(_scheme_exists(HIGH_PERFORMANCE_GUID))
            self.assertTrue(_scheme_exists("8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"))
            self.assertFalse(_scheme_exists(ULTIMATE_PERFORMANCE_GUID))


class TestGameModeState(unittest.TestCase):

    def test_is_active(self):
        cfg = _FakeConfig()
        cfg.game_mode_active = True
        self.assertTrue(GameModeManager.is_active(cfg))
        cfg.game_mode_active = False
        self.assertFalse(GameModeManager.is_active(cfg))
        # 无配置对象时返回 False
        self.assertFalse(GameModeManager.is_active(None))

    def test_save_state(self):
        cfg = _FakeConfig()
        mgr = GameModeManager(cfg)
        mgr._save_state(True)
        self.assertTrue(cfg.game_mode_active)
        self.assertTrue(cfg.saved)


if __name__ == "__main__":
    unittest.main(verbosity=2)
