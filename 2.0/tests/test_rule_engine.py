# -*- coding: utf-8 -*-

"""
规则引擎单元测试 v2.1
"""

import unittest
from datetime import datetime


class TestProcessRule(unittest.TestCase):
    """测试 ProcessRule 数据类的序列化"""

    def setUp(self):
        # 避免导入 Windows 特有模块，直接测试数据类结构
        from core.rule_engine import ProcessRule

        self.RuleClass = ProcessRule

    def test_to_dict_roundtrip(self):
        """测试规则对象到字典再回对象"""
        rule = self.RuleClass(
            name="test_rule",
            process_pattern="test.exe",
            match_type="exact",
            actions=["set_io_low", "set_cpu_eco"],
            enabled=True,
            profile_name="gaming",
            description="测试规则",
        )
        d = rule.to_dict()
        restored = self.RuleClass.from_dict(d)

        self.assertEqual(restored.name, "test_rule")
        self.assertEqual(restored.process_pattern, "test.exe")
        self.assertEqual(restored.match_type, "exact")
        self.assertEqual(restored.actions, ["set_io_low", "set_cpu_eco"])
        self.assertTrue(restored.enabled)
        self.assertEqual(restored.profile_name, "gaming")

    def test_to_dict_auto_created_at(self):
        """测试 created_at 为空时自动填充"""
        rule = self.RuleClass(name="auto_date", process_pattern="foo.exe")
        d = rule.to_dict()
        self.assertIn("created_at", d)
        self.assertTrue(len(d["created_at"]) > 0)

    def test_from_dict_empty(self):
        """测试空字典反序列化"""
        rule = self.RuleClass.from_dict({})
        self.assertEqual(rule.name, "")
        self.assertEqual(rule.match_type, "exact")
        self.assertTrue(rule.enabled)
        self.assertEqual(rule.actions, [])

    def test_from_dict_partial(self):
        """测试部分字典反序列化"""
        rule = self.RuleClass.from_dict({
            "name": "partial",
            "process_pattern": "*.tmp",
            "match_type": "wildcard",
        })
        self.assertEqual(rule.name, "partial")
        self.assertEqual(rule.match_type, "wildcard")
        self.assertTrue(rule.enabled)  # 默认值应保留
        self.assertEqual(rule.actions, [])  # 默认空列表

    def test_disabled_rule(self):
        """测试禁用规则"""
        rule = self.RuleClass(
            name="disabled",
            process_pattern="bad.exe",
            match_type="exact",
            enabled=False,
            actions=["kill"],
        )
        self.assertFalse(rule.enabled)
        d = rule.to_dict()
        self.assertFalse(d["enabled"])

    def test_all_match_types(self):
        """测试所有匹配方式"""
        rule = self.RuleClass(
            name="regex_rule",
            process_pattern=r"SGuard\d+\.exe",
            match_type="regex",
        )
        self.assertEqual(rule.match_type, "regex")
        d = rule.to_dict()
        self.assertEqual(d["match_type"], "regex")

    def test_special_chars_in_pattern(self):
        """测试进程名含特殊字符"""
        rule = self.RuleClass(
            name="special",
            process_pattern="AntiCheat Expert.exe",
            match_type="exact",
        )
        d = rule.to_dict()
        self.assertEqual(d["process_pattern"], "AntiCheat Expert.exe")


class TestGameProfile(unittest.TestCase):
    """测试 GameProfile 数据类的序列化"""

    def setUp(self):
        from core.profile_manager import GameProfile

        self.ProfileClass = GameProfile

    def test_to_dict_roundtrip(self):
        """测试预设对象到字典再回对象"""
        profile = self.ProfileClass(
            name="Valorant",
            description="瓦洛兰特优化方案",
            trigger_process="VALORANT.exe",
            rules=["ace_kill", "sguard_optimize"],
            ramdisk_enabled=True,
            memory_clean=True,
            io_priority_processes=["RiotClient.exe"],
        )
        d = profile.to_dict()
        restored = self.ProfileClass.from_dict(d)

        self.assertEqual(restored.name, "Valorant")
        self.assertEqual(restored.trigger_process, "VALORANT.exe")
        self.assertTrue(restored.ramdisk_enabled)
        self.assertTrue(restored.memory_clean)
        self.assertIn("ace_kill", restored.rules)

    def test_default_values(self):
        """测试默认值"""
        profile = self.ProfileClass(name="test", trigger_process="test.exe")
        self.assertFalse(profile.ramdisk_enabled)
        self.assertFalse(profile.memory_clean)
        self.assertTrue(profile.enabled)
        self.assertEqual(profile.rules, [])
        self.assertEqual(profile.io_priority_processes, [])

    def test_from_dict_empty(self):
        """测试空字典"""
        profile = self.ProfileClass.from_dict({})
        self.assertEqual(profile.name, "")
        self.assertEqual(profile.trigger_process, "")
        self.assertTrue(profile.enabled)

    def test_disabled_profile(self):
        """测试禁用预设"""
        profile = self.ProfileClass(
            name="off",
            trigger_process="off.exe",
            enabled=False,
        )
        self.assertFalse(profile.enabled)
        d = profile.to_dict()
        self.assertFalse(d["enabled"])


class TestWin32Constants(unittest.TestCase):
    """测试共享 Windows API 常量模块"""

    def test_constants_have_expected_values(self):
        """验证关键常量值正确"""
        from core.win32_constants import (
            PROCESS_ALL_ACCESS,
            MEM_COMMIT,
            MEM_RELEASE,
            IDLE_PRIORITY_CLASS,
            PROCESS_POWER_THROTTLING_INFORMATION,
            MemoryPurgeStandbyList,
        )

        self.assertEqual(PROCESS_ALL_ACCESS, 0x1F0FFF)
        self.assertEqual(MEM_COMMIT, 0x1000)
        self.assertEqual(MEM_RELEASE, 0x8000)
        self.assertEqual(IDLE_PRIORITY_CLASS, 0x40)
        self.assertEqual(PROCESS_POWER_THROTTLING_INFORMATION, 4)
        self.assertEqual(MemoryPurgeStandbyList, 0x4)

    def test_io_priority_hint_values(self):
        """验证 IO 优先级枚举值"""
        from core.win32_constants import IO_PRIORITY_HINT

        self.assertEqual(IO_PRIORITY_HINT.IoPriorityVeryLow, 0)
        self.assertEqual(IO_PRIORITY_HINT.IoPriorityLow, 1)
        self.assertEqual(IO_PRIORITY_HINT.IoPriorityNormal, 2)

    def test_structures_exist(self):
        """验证结构体定义存在"""
        from core.win32_constants import (
            PROCESS_POWER_THROTTLING_STATE,
            SYSTEM_FILECACHE_INFORMATION,
            MEMORY_COMBINE_INFORMATION_EX,
        )

        self.assertIsNotNone(PROCESS_POWER_THROTTLING_STATE)
        self.assertIsNotNone(SYSTEM_FILECACHE_INFORMATION)
        self.assertIsNotNone(MEMORY_COMBINE_INFORMATION_EX)

    def test_constant_consistency(self):
        """验证各模块使用的常量值一致"""
        from core.win32_constants import (
            PROCESS_ALL_ACCESS as SHARED_ALL_ACCESS,
            IDLE_PRIORITY_CLASS as SHARED_IDLE,
            ProcessIoPriority as SHARED_IO_PRIORITY,
        )

        # process_io_priority.py 中的值
        PIO_ALL_ACCESS = 0x1F0FFF
        PIO_IO_PRIORITY = 33

        self.assertEqual(SHARED_ALL_ACCESS, PIO_ALL_ACCESS)
        self.assertEqual(SHARED_IO_PRIORITY, PIO_IO_PRIORITY)


if __name__ == "__main__":
    unittest.main()
