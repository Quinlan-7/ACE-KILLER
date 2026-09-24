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
        self._imdisk_available = None  # 缓存检测结果

        # ACE 临时目录列表
        self.ace_temp_paths = [
            os.path.join(os.environ.get("TEMP", ""), "Tencent"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp", "Tencent"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Tencent", "ACE"),
            os.path.join(os.environ.get("PROGRAMDATA", ""), "Tencent", "ACE"),
        ]

        self._initialized = True

    def detect_imdisk(self) -> bool:
        """检测 ImDisk 是否已安装"""
        if self._imdisk_available is not None:
            return self._imdisk_available

        try:
            # 检查 imdisk.exe 是否在 PATH 中
            result = subprocess.run(
                "where imdisk.exe", shell=True,
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0:
                self._imdisk_available = True
                logger.success("检测到 ImDisk")
                return True
        except Exception:
            pass

        # 检查常见安装路径
        common_paths = [
            os.path.expandvars(r"%ProgramFiles%\ImDisk\imdisk.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\ImDisk\imdisk.exe"),
            r"C:\Program Files\ImDisk\imdisk.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                self._imdisk_available = True
                logger.success(f"检测到 ImDisk: {path}")
                return True

        self._imdisk_available = False
        return False

    def create_imdisk_ramdisk(self, size_mb: int = 2048, letter: str = None) -> bool:
        """使用 ImDisk 创建真正的内存盘"""
        letter = letter or self.ram_disk_letter
        try:
            imdisk_path = None
            result = subprocess.run(
                "where imdisk.exe", shell=True,
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0:
                imdisk_path = result.stdout.strip().split("\n")[0].strip()

            if not imdisk_path:
                for path in [
                    os.path.expandvars(r"%ProgramFiles%\ImDisk\imdisk.exe"),
                    os.path.expandvars(r"%ProgramFiles(x86)%\ImDisk\imdisk.exe"),
                ]:
                    if os.path.exists(path):
                        imdisk_path = path
                        break

            if not imdisk_path:
                logger.error("未找到 ImDisk 可执行文件")
                return False

            # 创建 RAM 盘: 格式化为 NTFS
            cmd = (
                f'"{imdisk_path}" -a -s {size_mb}M -m {letter}: '
                f'-p "/fs:ntfs /q /y /v:ACE_RAMDISK"'
            )
            subprocess.run(cmd, shell=True, check=True, timeout=10)
            logger.success(f"ImDisk RAM 盘创建成功: {letter}: ({size_mb}MB)")
            return True

        except subprocess.TimeoutExpired:
            logger.error("ImDisk 创建超时")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"ImDisk 创建失败: {e}")
            return False
        except Exception as e:
            logger.error(f"ImDisk 创建异常: {e}")
            return False

    def setup_ramdisk(self):
        """创建 RAM 盘并设置重定向

        优先使用 ImDisk（真正的内存盘），
        回退到 subst（虚拟目录映射）

        Returns:
            bool: 是否成功
        """
        try:
            ram_path = f"{self.ram_disk_letter}:\\"

            if os.path.exists(ram_path):
                logger.success(f"RAM 盘已存在: {ram_path}")
            else:
                # 优先使用 ImDisk
                if self.detect_imdisk():
                    if self.create_imdisk_ramdisk(2048, self.ram_disk_letter):
                        logger.success("使用 ImDisk 真实内存盘")
                    else:
                        logger.warning("ImDisk 创建失败，使用 subst 回退方案")
                        self._create_subst_ramdisk()
                else:
                    logger.info("未检测到 ImDisk，使用 subst 虚拟驱动器")
                    self._create_subst_ramdisk()

            self._setup_redirects()
            return True

        except Exception as e:
            logger.error(f"RAM 盘创建失败: {e}")
            return False

    def _create_subst_ramdisk(self):
        """使用 subst 创建虚拟驱动器（回退方案）"""
        ram_path = f"{self.ram_disk_letter}:\\"
        temp_path = os.path.join(os.environ["TEMP"], "ACE_RAMDisk")
        os.makedirs(temp_path, exist_ok=True)
        subprocess.run(
            f"subst {self.ram_disk_letter}: \"{temp_path}\"",
            shell=True, check=True, capture_output=True
        )
        logger.success(f"虚拟驱动器创建成功: {ram_path}")

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

        v2.2: 增强 —— 同时清理自建的 ImDisk 内存盘（按卷标识别，避免误删用户盘）

        Returns:
            bool: 是否成功
        """
        try:
            # 移除 subst 虚拟驱动器
            subprocess.run(
                f"subst {self.ram_disk_letter}: /D",
                shell=True, check=False, capture_output=True
            )

            # v2.2: 若 RAM 盘卷标为 ACE_RAMDISK（自建 ImDisk 盘），删除之
            try:
                result = subprocess.run(
                    f"vol {self.ram_disk_letter}:",
                    shell=True, capture_output=True, text=True, timeout=5
                )
                vol_out = (result.stdout or "") + (result.stderr or "")
                if "ACE_RAMDISK" in vol_out.upper():
                    imdisk_path = self._find_imdisk_path()
                    if imdisk_path:
                        subprocess.run(
                            f'"{imdisk_path}" -D -m {self.ram_disk_letter}:',
                            shell=True, check=False, capture_output=True, timeout=10
                        )
                        logger.success(
                            f"已卸载自建 ImDisk RAM 盘: {self.ram_disk_letter}:"
                        )
            except Exception as e:
                logger.debug(f"清理 ImDisk RAM 盘失败: {e}")

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

    def _find_imdisk_path(self):
        """查找 imdisk.exe 完整路径"""
        try:
            result = subprocess.run(
                "where imdisk.exe", shell=True,
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split("\n")[0].strip()
        except Exception:
            pass
        for path in [
            os.path.expandvars(r"%ProgramFiles%\ImDisk\imdisk.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\ImDisk\imdisk.exe"),
        ]:
            if os.path.exists(path):
                return path
        return None

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
                _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                _kernel32.GetDiskFreeSpaceExW.argtypes = [
                    ctypes.c_wchar_p,
                    ctypes.POINTER(ctypes.c_ulonglong),
                    ctypes.POINTER(ctypes.c_ulonglong),
                    ctypes.POINTER(ctypes.c_ulonglong),
                ]
                _kernel32.GetDiskFreeSpaceExW.restype = ctypes.c_int
                free_bytes = ctypes.c_ulonglong(0)
                total_bytes = ctypes.c_ulonglong(0)
                if _kernel32.GetDiskFreeSpaceExW(
                    ram_path,
                    ctypes.byref(free_bytes),
                    ctypes.byref(total_bytes),
                    None,
                ):
                    info["total_gb"] = round(total_bytes.value / (1024**3), 1)
                    info["free_gb"] = round(free_bytes.value / (1024**3), 1)
                    info["used_gb"] = round(
                        (total_bytes.value - free_bytes.value) / (1024**3), 1
                    )
            except Exception:
                pass

        return info
