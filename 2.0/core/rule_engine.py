#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
进程规则引擎 v2.1
自定义进程匹配 + 限制动作
"""

import fnmatch
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from loguru import logger

from config.config_manager import ConfigManager
from utils.process_io_priority import (
    get_io_priority_manager,
    PerformanceConfigApplier,
)
from core.system_utils import get_program_path


@dataclass
class ProcessRule:
    """进程规则定义"""

    name: str
    process_pattern: str
    match_type: str = "exact"  # exact | wildcard | regex
    actions: list = field(default_factory=list)
    enabled: bool = True
    profile_name: Optional[str] = None
    created_at: str = ""
    description: str = ""

    def to_dict(self):
        return {
            "name": self.name,
            "process_pattern": self.process_pattern,
            "match_type": self.match_type,
            "actions": self.actions,
            "enabled": self.enabled,
            "profile_name": self.profile_name,
            "created_at": self.created_at or datetime.now().isoformat(),
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data.get("name", ""),
            process_pattern=data.get("process_pattern", ""),
            match_type=data.get("match_type", "exact"),
            actions=data.get("actions", []),
            enabled=data.get("enabled", True),
            profile_name=data.get("profile_name"),
            created_at=data.get("created_at", ""),
            description=data.get("description", ""),
        )


class RuleEngine:
    """规则引擎 - 单例"""

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
        self._rules: list[ProcessRule] = []
        self._applied_cache: dict[int, list[str]] = {}  # pid -> [rule_names]
        self._load_rules()
        self._initialized = True

    def _load_rules(self):
        """从配置加载规则"""
        try:
            raw_rules = getattr(self.config, "rules", [])
            self._rules = [ProcessRule.from_dict(r) for r in raw_rules]
            logger.debug(f"已加载 {len(self._rules)} 条规则")
        except Exception as e:
            logger.error(f"加载规则失败: {e}")
            self._rules = []

    def _save_rules(self):
        """保存规则到配置"""
        try:
            self.config.rules = [r.to_dict() for r in self._rules]
            self.config.save_config()
        except Exception as e:
            logger.error(f"保存规则失败: {e}")

    def get_matching_rules(self, process_name: str) -> list[ProcessRule]:
        """获取匹配进程名称的所有已启用规则"""
        matches = []
        for rule in self._rules:
            if not rule.enabled:
                continue
            if self._match_process(rule.process_pattern, process_name, rule.match_type):
                matches.append(rule)
        return matches

    def _match_process(self, pattern: str, name: str, match_type: str) -> bool:
        """匹配进程名称"""
        try:
            if match_type == "exact":
                return pattern.lower() == name.lower()
            elif match_type == "wildcard":
                return fnmatch.fnmatch(name.lower(), pattern.lower())
            elif match_type == "regex":
                return bool(re.search(pattern, name, re.IGNORECASE))
            return False
        except Exception:
            return False

    def apply_rules(self, pid: int, process_name: str) -> list[str]:
        """应用匹配规则到进程，返回已应用的动作描述列表"""
        applied = []
        rules = self.get_matching_rules(process_name)
        if not rules:
            return applied

        for rule in rules:
            for action in rule.actions:
                try:
                    result = self._apply_action(pid, process_name, action)
                    if result:
                        applied.append(f"{rule.name}:{action.get('type')}")
                        logger.info(
                            f"规则 [{rule.name}] 应用 {action.get('type')} "
                            f"到 {process_name} (PID:{pid})"
                        )
                except Exception as e:
                    logger.error(
                        f"规则 [{rule.name}] 动作 {action.get('type')} "
                        f"应用于 {process_name} 失败: {e}"
                    )

        if applied:
            self._applied_cache[pid] = applied
        return applied

    def _apply_action(self, pid: int, name: str, action: dict) -> bool:
        """执行单个动作"""
        action_type = action.get("type", "")
        value = action.get("value")

        if action_type == "terminate" and value:
            import psutil
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                logger.warning(f"已终止进程: {name} (PID:{pid})")
                return True
            except Exception:
                return False

        if action_type == "ramdisk_redirect":
            from core.ramdisk_manager import RamdiskManager
            rm = RamdiskManager()
            return rm.setup_ramdisk()

        applier = PerformanceConfigApplier()
        config = {}

        if action_type == "io_priority":
            config["io_priority"] = int(value) if value is not None else 0
        elif action_type == "cpu_priority":
            config["cpu_priority"] = str(value) if value else "IDLE"
        elif action_type == "cpu_affinity":
            config["max_cores"] = int(value) if value else 1
        elif action_type == "power_throttling":
            config["power_throttling"] = bool(value)

        if config:
            success, _ = applier.apply(pid, config)
            return success

        return False

    def get_applied_rules(self, pid: int) -> list[str]:
        """获取已应用到进程的规则"""
        return self._applied_cache.get(pid, [])

    def clear_applied_cache(self):
        """清理已应用缓存"""
        self._applied_cache.clear()

    def add_rule(self, rule: ProcessRule):
        """添加规则"""
        self._rules.append(rule)
        self._save_rules()
        logger.success(f"已添加规则: {rule.name}")

    def remove_rule(self, name: str):
        """删除规则"""
        self._rules = [r for r in self._rules if r.name != name]
        self._save_rules()
        logger.success(f"已删除规则: {name}")

    def update_rule(self, rule: ProcessRule):
        """更新规则"""
        for i, r in enumerate(self._rules):
            if r.name == rule.name:
                self._rules[i] = rule
                self._save_rules()
                logger.success(f"已更新规则: {rule.name}")
                return
        logger.warning(f"未找到要更新的规则: {rule.name}")

    def list_rules(self) -> list[ProcessRule]:
        """列出所有规则"""
        return list(self._rules)

    def get_rule(self, name: str) -> Optional[ProcessRule]:
        """获取单条规则"""
        for r in self._rules:
            if r.name == name:
                return r
        return None


def get_rule_engine() -> RuleEngine:
    """获取规则引擎单例"""
    return RuleEngine()
