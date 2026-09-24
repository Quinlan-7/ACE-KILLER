#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ACE-KILLER主程序入口
"""

import os
import sys
import time
import queue

from config.config_manager import ConfigManager
from core.process_monitor import GameProcessMonitor
from core.system_utils import run_as_admin, check_single_instance
from utils.logger import setup_logger, logger
from utils.notification import find_icon_path, send_notification, create_notification_thread
from utils.process_io_priority import get_io_priority_service

from ui.main_window import create_gui


def main():
    """主程序入口函数 (v2.0)"""
    # 检查管理员权限
    if not run_as_admin():
        return
    
    # 检查单实例运行
    if not check_single_instance():
        return
    
    # 创建配置管理器
    config_manager = ConfigManager()
    
    # 配置日志系统
    setup_logger(
        config_manager.log_dir,
        config_manager.log_retention_days,
        config_manager.log_rotation,
        config_manager.debug_mode
    )
    
    # v2.0: 处理 --delay 参数（延迟启动）
    delay_seconds = 0
    if "--delay" in sys.argv:
        try:
            idx = sys.argv.index("--delay")
            if idx + 1 < len(sys.argv):
                delay_seconds = int(sys.argv[idx + 1])
        except (ValueError, IndexError):
            pass

    if delay_seconds > 0:
        logger.info(f"延迟启动 {delay_seconds} 秒...")
        time.sleep(delay_seconds)

    # v2.0: 首次运行向导
    if config_manager.first_run:
        logger.info("首次运行，启动设置向导")
        from PySide6.QtWidgets import QApplication
        _app = QApplication.instance() or QApplication(sys.argv)
        from ui.dialogs.setup_wizard import SetupWizard
        wizard = SetupWizard()
        wizard.exec_()
        # v2.2: 重新加载配置，使向导中启用的设置（监控/RAM盘等）真正生效
        config_manager = ConfigManager()

    # 创建进程监控器
    monitor = GameProcessMonitor(config_manager)
    
    # 创建并启动I/O优先级服务
    io_priority_service = get_io_priority_service(config_manager)
    io_priority_service.start_service()
    
    # v2.0: 启动磁盘 IO 统计
    from core.disk_stats import get_disk_stats
    get_disk_stats().start_monitoring()
    
    # 现在日志系统已初始化，可以记录启动信息
    logger.debug("🟩 ACE-KILLER v2.2.3 程序已启动！")
    
    # 查找图标文件
    icon_path = find_icon_path()
    
    # 创建通知线程
    notification_thread_obj, stop_event = create_notification_thread(
        monitor.message_queue,
        icon_path
    )
    
    # 创建并运行PySide6图形界面
    app, window = create_gui(monitor, icon_path)
    
    # 显示欢迎通知
    from utils.version_checker import GITHUB_REPO
    buttons = [
        {'text': '访问项目主页', 'action': 'open_url', 'launch': f'https://github.com/{GITHUB_REPO}'},
        {'text': '下载最新版本', 'action': 'open_url', 'launch': f'https://github.com/{GITHUB_REPO}/releases/latest'}
    ]
    
    send_notification(
        title="ACE-KILLER",
        message=f"🚀 欢迎使用 ACE-KILLER ！\nACE SSD 保护 | RAM 盘重定向 | 内存清理",
        icon_path=icon_path,
        buttons=buttons,
        silent=True
    )
    

    try:
        # 运行应用（这会阻塞主线程直到应用程序退出）
        sys.exit(app.exec())
    except KeyboardInterrupt:
        # 处理键盘中断
        pass
    finally:
        # 确保停止所有线程
        if monitor.running:
            monitor.running = False
            # 停止所有游戏监控（v2.2: 修复 stop_all_monitors 不存在导致的退出异常）
            monitor.stop_monitors()
            
        # 停止I/O优先级服务
        if io_priority_service and io_priority_service.running:
            io_priority_service.stop_service()
            
        # 设置通知线程停止事件
        stop_event.set()
        # 等待通知线程结束
        notification_thread_obj.join(timeout=0.5)
        
        logger.debug("🔴 ACE-KILLER 程序已终止！")


if __name__ == "__main__":
    main()
