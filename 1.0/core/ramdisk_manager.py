#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RAM 盘管理模块
集成自 ACE SSD 保护工具，提供 RAM 盘创建和目录重定向功能
"""

import os
import sys
import subprocess
import ctypes
from utils.logger import logger


class RamdiskManager:
    """RAM 盘管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RamdiskManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.ram_disk_letter = "R"
        self.redirected_count = 0

        # ACE 临时目录列表
        self.ace_temp_paths = [
            os.path.join(os.environ.get("TEMP", ""), "Tencent"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp", "Tencent"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Tencent", "ACE"),
            os.path.join(os.environ.get("PROGRAMDATA", ""), "Tencent", "ACE"),
        ]

        self._initialized = True

    def setup_ramdisk(self):
        """创建 RAM 盘并设置重定向

        Returns:
            bool: 是否成功
        """
        try:
            ram_path = f"{self.ram_disk_letter}:\\"

            if os.path.exists(ram_path):
                logger.success(f"RAM 盘已存在: {ram_path}")
            else:
                temp_path = os.path.join(os.environ["TEMP"], "ACE_RAMDisk")
                os.makedirs(temp_path, exist_ok=True)
                subprocess.run(
                    f"subst {self.ram_disk_letter}: \"{temp_path}\"",
                    shell=True, check=True, capture_output=True
                )
                logger.success(f"RAM 盘创建成功: {ram_path}")

            self._setup_redirects()
            return True

        except Exception as e:
            logger.error(f"RAM 盘创建失败: {e}")
            return False

    def _setup_redirects(self):
        """设置 ACE 临时目录重定向到 RAM 盘"""
        self.redirected_count = 0

        for temp_path in self.ace_temp_paths:
            try:
                if not os.path.exists(temp_path):
                    continue

                if os.path.islink(temp_path):
                    continue

                backup_path = f"{temp_path}_backup"
                if os.path.exists(temp_path) and not os.path.exists(backup_path):
                    os.rename(temp_path, backup_path)
                    logger.info(f"已备份目录: {temp_path}")

                ram_target = os.path.join(
                    f"{self.ram_disk_letter}:\\ACE_Temp",
                    os.path.basename(temp_path)
                )
                os.makedirs(ram_target, exist_ok=True)

                subprocess.run(
                    f"mklink /D \"{temp_path}\" \"{ram_target}\"",
                    shell=True, check=True, capture_output=True
                )

                logger.success(
                    f"重定向: {os.path.basename(temp_path)} -> RAM 盘"
                )
                self.redirected_count += 1

            except Exception:
                continue

        if self.redirected_count > 0:
            logger.success(f"成功重定向 {self.redirected_count} 个目录到 RAM 盘")

    def cleanup_ramdisk(self):
        """清理 RAM 盘和重定向

        Returns:
            bool: 是否成功
        """
        try:
            # 移除 subst 虚拟驱动器
            subprocess.run(
                f"subst {self.ram_disk_letter}: /D",
                shell=True, check=False, capture_output=True
            )

            # 恢复原始目录
            for temp_path in self.ace_temp_paths:
                try:
                    if os.path.islink(temp_path):
                        os.unlink(temp_path)
                        backup_path = f"{temp_path}_backup"
                        if os.path.exists(backup_path):
                            os.rename(backup_path, temp_path)
                except Exception:
                    continue

            logger.success("RAM 盘已清理")
            return True

        except Exception as e:
            logger.error(f"清理 RAM 盘失败: {e}")
            return False

    def get_ramdisk_info(self):
        """获取 RAM 盘信息

        Returns:
            dict: RAM 盘信息
        """
        info = {
            "exists": False,
            "total_gb": 0,
            "used_gb": 0,
            "free_gb": 0,
            "redirected_dirs": self.redirected_count,
        }

        ram_path = f"{self.ram_disk_letter}:\\"
        if os.path.exists(ram_path):
            info["exists"] = True
            try:
                usage = ctypes._kernel32.GetDiskFreeSpaceExW(ram_path)
                if usage:
                    free_bytes, total_bytes, _ = usage
                    info["total_gb"] = round(total_bytes / (1024**3), 1)
                    info["free_gb"] = round(free_bytes / (1024**3), 1)
                    info["used_gb"] = round(
                        (total_bytes - free_bytes) / (1024**3), 1
                    )
            except Exception:
                pass

        return info
