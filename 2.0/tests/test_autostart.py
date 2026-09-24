#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
自启动模块单元测试 v2.2
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.autostart import (
    _build_arguments,
    _task_name,
    _get_shortcut_path,
    _get_startup_folder,
    get_program_path,
)


class TestAutoStart(unittest.TestCase):

    def test_build_arguments(self):
        self.assertEqual(_build_arguments(0), "--minimized")
        self.assertEqual(_build_arguments(30), "--minimized --delay 30")
        self.assertEqual(_build_arguments(-1), "--minimized")

    def test_task_name(self):
        self.assertEqual(_task_name("ACE-KILLER"), "ACE-KILLER-AutoStart")
        self.assertEqual(_task_name(), "ACE-KILLER-AutoStart")

    def test_startup_folder(self):
        folder = _get_startup_folder()
        self.assertTrue(folder.lower().endswith("startup"))
        self.assertTrue(os.path.isabs(folder))

    def test_shortcut_path(self):
        path = _get_shortcut_path("ACE-KILLER")
        self.assertTrue(path.endswith("ACE-KILLER.lnk"))

    def test_program_path(self):
        path = get_program_path()
        self.assertTrue(os.path.isabs(path))


if __name__ == "__main__":
    unittest.main(verbosity=2)
