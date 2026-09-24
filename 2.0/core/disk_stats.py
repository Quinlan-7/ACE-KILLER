#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
磁盘 IO 统计数据采集 v2.1
跟踪 ACE 相关进程的读写量，展示保护效果
"""

import threading
import time
from collections import defaultdict
from datetime import datetime
from loguru import logger
import psutil


class DiskStatsCollector:
    """磁盘 IO 统计采集器 - 单例"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._running = False
        self._thread = None
        self._lock_data = threading.Lock()

        # 进程 IO 数据: {pid: {"name": str, "read_bytes": int, "write_bytes": int, "timestamp": float}}
        self._current = {}
        self._previous = {}

        # 历史累计
        self._totals = defaultdict(lambda: {"read": 0, "write": 0})

        # 受保护进程的 IO (被限制的)
        self._protected_read = 0
        self._protected_write = 0

        # 监控的进程名列表
        self._watch_list = [
            "SGuard64.exe", "ACE-Tray.exe", "ACE-Guard.exe",
            "SGuardSvc64.exe", "SGuardwnd.exe", "ACE-Base.exe",
            "ACE-Base-Client.exe",
        ]

        self._initialized = True
        logger.debug("磁盘 IO 统计采集器已初始化")

    def start_monitoring(self):
        """启动 IO 统计后台线程"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._collector_loop, daemon=True)
        self._thread.start()
        logger.debug("磁盘 IO 统计已启动")

    def stop_monitoring(self):
        """停止 IO 统计"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.debug("磁盘 IO 统计已停止")

    def _collector_loop(self):
        """后台采集循环"""
        while self._running:
            try:
                self._collect_snapshot()
            except Exception as e:
                logger.error(f"IO 统计采集异常: {e}")
            time.sleep(2)

    def _collect_snapshot(self):
        """采集当前快照"""
        now = time.time()
        snapshot = {}

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = proc.info["name"] or ""
                if not any(w.lower() == name.lower() for w in self._watch_list):
                    continue

                pid = proc.info["pid"]
                io = proc.io_counters()
                if io:
                    snapshot[pid] = {
                        "name": name,
                        "read_bytes": io.read_bytes,
                        "write_bytes": io.write_bytes,
                        "timestamp": now,
                    }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception:
                continue

        # 计算增量
        with self._lock_data:
            for pid, curr in snapshot.items():
                prev = self._previous.get(pid)
                if prev:
                    read_delta = max(0, curr["read_bytes"] - prev["read_bytes"])
                    write_delta = max(0, curr["write_bytes"] - prev["write_bytes"])
                    self._totals[curr["name"]]["read"] += read_delta
                    self._totals[curr["name"]]["write"] += write_delta

            self._previous = {p: dict(v) for p, v in snapshot.items()}
            self._current = snapshot

    def mark_protected(self, process_name: str):
        """标记进程 IO 已受保护（用于展示减少量）"""
        name_lower = process_name.lower()
        for pid, info in list(self._current.items()):
            if info["name"].lower() == name_lower:
                prev = self._previous.get(pid)
                if prev:
                    self._protected_read += max(0, info["read_bytes"] - prev["read_bytes"])
                    self._protected_write += max(0, info["write_bytes"] - prev["write_bytes"])
                break

    def get_process_stats(self, process_name: str) -> dict:
        """获取指定进程的 IO 统计"""
        result = {
            "read_bytes_total": 0,
            "write_bytes_total": 0,
            "read_mb": 0.0,
            "write_mb": 0.0,
        }
        name_lower = process_name.lower()
        for pname, data in self._totals.items():
            if pname.lower() == name_lower:
                result["read_bytes_total"] = data["read"]
                result["write_bytes_total"] = data["write"]
                result["read_mb"] = round(data["read"] / (1024 * 1024), 2)
                result["write_mb"] = round(data["write"] / (1024 * 1024), 2)
                break
        return result

    def get_all_stats(self) -> dict:
        """获取所有进程统计"""
        result = {}
        with self._lock_data:
            for pname, data in self._totals.items():
                result[pname] = {
                    "read_mb": round(data["read"] / (1024 * 1024), 2),
                    "write_mb": round(data["write"] / (1024 * 1024), 2),
                }
        return result

    def get_total_protected_io(self) -> dict:
        """获取受保护的 IO 总量"""
        return {
            "read_mb": round(self._protected_read / (1024 * 1024), 2),
            "write_mb": round(self._protected_write / (1024 * 1024), 2),
        }

    def add_watch_name(self, process_name: str):
        """添加监控进程名"""
        if process_name not in self._watch_list:
            self._watch_list.append(process_name)

    def get_active_processes(self) -> list:
        """获取当前活跃的被监控进程"""
        result = []
        with self._lock_data:
            for pid, info in self._current.items():
                result.append({"pid": pid, "name": info["name"]})
        return result


def get_disk_stats() -> DiskStatsCollector:
    """获取磁盘统计采集器单例"""
    return DiskStatsCollector()
