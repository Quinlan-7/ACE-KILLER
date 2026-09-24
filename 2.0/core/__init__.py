"""
核心功能模块 v2.2
=================
注意：本包刻意保持“轻量导入”——不在 __init__ 中急切导入子模块，
避免 config.config_manager → core.system_utils → core 包 → process_monitor
→ profile_manager → config.config_manager 的循环导入问题。

子模块请通过 `from core.xxx import Y` 方式显式导入。
"""

__all__ = [
    "GameProcessMonitor", "run_as_admin",
    "enable_auto_start", "disable_auto_start",
    "RamdiskManager",
    "DiskStatsCollector", "get_disk_stats",
]
