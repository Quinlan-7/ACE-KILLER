#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WMI 进程事件监控 v2.0
使用 WMI 事件订阅替代轮询，实时监听进程创建和终止
"""

import threading
import time
import pythoncom
from loguru import logger


class WmiProcessMonitor:
    """WMI 进程事件监控器"""

    def __init__(self):
        self._running = False
        self._thread = None
        self._on_created = []
        self._on_terminated = []
        self._wmi_available = False
        self._check_wmi_available()

    def _check_wmi_available(self):
        """检查 WMI 是否可用"""
        try:
            import win32com.client
            self._wmi_available = True
        except ImportError:
            self._wmi_available = False
            logger.warning("win32com 未安装，WMI 监控不可用，将使用轮询模式")
        except Exception as e:
            self._wmi_available = False
            logger.warning(f"WMI 初始化失败: {e}")

    @property
    def available(self) -> bool:
        return self._wmi_available

    def on_process_created(self, callback):
        """注册进程创建回调"""
        if callback not in self._on_created:
            self._on_created.append(callback)

    def on_process_terminated(self, callback):
        """注册进程终止回调"""
        if callback not in self._on_terminated:
            self._on_terminated.append(callback)

    def start(self):
        """启动 WMI 监控"""
        if not self._wmi_available:
            logger.warning("WMI 不可用，无法启动 WMI 监控")
            return False

        if self._running:
            return True

        self._running = True
        self._thread = threading.Thread(target=self._wmi_loop, daemon=True)
        self._thread.start()
        logger.success("WMI 进程监控已启动")
        return True

    def stop(self):
        """停止 WMI 监控"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        logger.info("WMI 进程监控已停止")

    def _wmi_loop(self):
        """WMI 事件订阅循环"""
        try:
            pythoncom.CoInitialize()
            import win32com.client

            wmi = win32com.client.GetObject("winmgmts:\\\\.\\root\\cimv2")

            # 订阅进程创建事件
            created_wql = "SELECT * FROM __InstanceCreationEvent WITHIN 1 WHERE TargetInstance ISA 'Win32_Process'"
            created_sink = wmi.ExecNotificationQuery(created_wql)

            # 订阅进程终止事件
            deleted_wql = "SELECT * FROM __InstanceDeletionEvent WITHIN 1 WHERE TargetInstance ISA 'Win32_Process'"
            deleted_sink = wmi.ExecNotificationQuery(deleted_wql)

            logger.debug("WMI 事件订阅已建立")

            poll_interval = 0.5

            while self._running:
                try:
                    # 检查进程创建事件
                    event = created_sink.NextEvent(poll_interval)
                    if event:
                        try:
                            proc = event.TargetInstance
                            name = getattr(proc, "Name", "")
                            pid = getattr(proc, "ProcessId", 0)
                            if name:
                                for cb in self._on_created:
                                    try:
                                        cb(name, pid)
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                except Exception:
                    pass

                try:
                    # 检查进程终止事件
                    event = deleted_sink.NextEvent(poll_interval)
                    if event:
                        try:
                            proc = event.TargetInstance
                            name = getattr(proc, "Name", "")
                            pid = getattr(proc, "ProcessId", 0)
                            if name:
                                for cb in self._on_terminated:
                                    try:
                                        cb(name, pid)
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"WMI 监控循环异常: {e}")
            self._running = False
        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass


def get_wmi_monitor() -> WmiProcessMonitor:
    """获取 WMI 监控器"""
    return WmiProcessMonitor()
