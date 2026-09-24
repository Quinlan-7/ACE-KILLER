#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
通知模块单元测试 v2.2
（不实际弹出 Windows Toast）
"""

import os
import sys
import threading
import queue
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.notification import find_icon_path, notification_thread, send_notification


class TestNotification(unittest.TestCase):

    def test_find_icon_path(self):
        # 返回 str 或 None，路径若存在则必须有效
        result = find_icon_path()
        self.assertTrue(result is None or os.path.exists(result))

    def test_find_icon_path_missing_returns_none(self):
        with mock.patch("os.path.exists", return_value=False):
            self.assertIsNone(find_icon_path())

    def test_send_notification_with_missing_icon(self):
        # 图标不存在时不应抛出异常（返回 False 或 True 均可，但绝不能崩溃）
        with mock.patch("os.path.exists", return_value=False):
            try:
                send_notification("测试", "测试内容", icon_path="C:\\不存在的图标.ico")
            except Exception as e:
                self.fail(f"send_notification 不应抛出异常: {e}")

    def test_notification_thread_stop_event(self):
        """通知线程应能响应停止事件"""
        msg_queue = queue.Queue()
        stop_event = threading.Event()
        icon_path = None

        thread = threading.Thread(
            target=notification_thread,
            args=(msg_queue, icon_path, stop_event),
            daemon=True,
        )
        thread.start()
        stop_event.set()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main(verbosity=2)
