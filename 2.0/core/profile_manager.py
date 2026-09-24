#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
游戏场景预设管理器 v2.1
命名 Profile 系统 - 自动触发场景切换
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from loguru import logger

from config.config_manager import ConfigManager


@dataclass
class GameProfile:
    """游戏场景预设"""

    name: str
    description: str = ""
    trigger_process: str = ""
    rules: list = field(default_factory=list)  # 关联的规则名称列表
    ramdisk_enabled: bool = False
    memory_clean: bool = False
    io_priority_processes: list = field(default_factory=list)
    enabled: bool = True
    created_at: str = ""

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "trigger_process": self.trigger_process,
            "rules": self.rules,
            "ramdisk_enabled": self.ramdisk_enabled,
            "memory_clean": self.memory_clean,
            "io_priority_processes": self.io_priority_processes,
            "enabled": self.enabled,
            "created_at": self.created_at or datetime.now().isoformat(),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            trigger_process=data.get("trigger_process", ""),
            rules=data.get("rules", []),
            ramdisk_enabled=data.get("ramdisk_enabled", False),
            memory_clean=data.get("memory_clean", False),
            io_priority_processes=data.get("io_priority_processes", []),
            enabled=data.get("enabled", True),
            created_at=data.get("created_at", ""),
        )


class ProfileManager:
    """场景预设管理器 - 单例"""

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
        self.config = ConfigManager()
        self._profiles: list[GameProfile] = []
        self._active_profile: Optional[GameProfile] = None
        self._previous_settings = {}
        self._load_profiles()
        self._initialized = True

    @property
    def active_profile(self) -> Optional[GameProfile]:
        return self._active_profile

    def _load_profiles(self):
        """从配置加载场景预设"""
        try:
            raw = getattr(self.config, "profiles", [])
            self._profiles = [GameProfile.from_dict(p) for p in raw]
            logger.debug(f"已加载 {len(self._profiles)} 个场景预设")
        except Exception as e:
            logger.error(f"加载场景预设失败: {e}")
            self._profiles = []

    def _save_profiles(self):
        """保存场景预设到配置"""
        try:
            self.config.profiles = [p.to_dict() for p in self._profiles]
            self.config.save_config()
        except Exception as e:
            logger.error(f"保存场景预设失败: {e}")

    def list_profiles(self) -> list[GameProfile]:
        return list(self._profiles)

    def get_profile(self, name: str) -> Optional[GameProfile]:
        for p in self._profiles:
            if p.name == name:
                return p
        return None

    def add_profile(self, profile: GameProfile):
        self._profiles.append(profile)
        self._save_profiles()
        logger.success(f"已添加场景预设: {profile.name}")

    def remove_profile(self, name: str):
        self._profiles = [p for p in self._profiles if p.name != name]
        if self._active_profile and self._active_profile.name == name:
            self._active_profile = None
        self._save_profiles()
        logger.success(f"已删除场景预设: {name}")

    def update_profile(self, profile: GameProfile):
        for i, p in enumerate(self._profiles):
            if p.name == profile.name:
                self._profiles[i] = profile
                self._save_profiles()
                logger.success(f"已更新场景预设: {profile.name}")
                return
        logger.warning(f"未找到要更新的场景预设: {profile.name}")

    def activate_profile(self, name: str) -> bool:
        """激活场景预设"""
        profile = self.get_profile(name)
        if not profile:
            logger.error(f"场景预设不存在: {name}")
            return False

        try:
            # 保存当前设置以便恢复
            self._previous_settings = {
                "ramdisk_enabled": self.config.ramdisk_enabled,
                "io_priority_processes": list(getattr(self.config, "io_priority_processes", [])),
            }

            # 应用 RAM 盘设置
            if profile.ramdisk_enabled:
                from core.ramdisk_manager import RamdiskManager
                rm = RamdiskManager()
                rm.setup_ramdisk()

            # 应用 IO 优先级设置
            if profile.io_priority_processes:
                self.config.io_priority_processes = profile.io_priority_processes
                self.config.save_config()

            # 清理内存
            if profile.memory_clean:
                try:
                    from utils.memory_cleaner import get_memory_cleaner
                    mc = get_memory_cleaner()
                    mc.clean_all()
                except Exception as e:
                    logger.warning(f"场景预设内存清理失败: {e}")

            self._active_profile = profile
            logger.success(f"已激活场景预设: {profile.name}")
            return True

        except Exception as e:
            logger.error(f"激活场景预设失败: {e}")
            return False

    def deactivate_profile(self) -> bool:
        """停用当前场景预设，恢复之前的设置"""
        if not self._active_profile:
            return True

        try:
            # 恢复之前保存的设置
            if "ramdisk_enabled" in self._previous_settings:
                if not self._previous_settings["ramdisk_enabled"]:
                    from core.ramdisk_manager import RamdiskManager
                    rm = RamdiskManager()
                    rm.cleanup_ramdisk()

            if "io_priority_processes" in self._previous_settings:
                self.config.io_priority_processes = self._previous_settings["io_priority_processes"]
                self.config.save_config()

            name = self._active_profile.name
            self._active_profile = None
            self._previous_settings = {}
            logger.success(f"已停用场景预设: {name}")
            return True

        except Exception as e:
            logger.error(f"停用场景预设失败: {e}")
            return False

    def check_trigger(self, process_name: str) -> Optional[str]:
        """检查进程名是否匹配任一预设的触发器"""
        if not process_name:
            return None
        proc_lower = process_name.lower()
        for profile in self._profiles:
            if not profile.enabled or not profile.trigger_process:
                continue
            if proc_lower == profile.trigger_process.lower():
                logger.info(f"进程 [{process_name}] 触发场景预设: {profile.name}")
                return profile.name
        return None


def get_profile_manager() -> ProfileManager:
    """获取场景预设管理器单例"""
    return ProfileManager()
