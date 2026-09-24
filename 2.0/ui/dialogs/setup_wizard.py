#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
首次运行设置向导 v2.0
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QCheckBox, QComboBox, QGroupBox, QWidget, QStackedWidget,
    QRadioButton, QButtonGroup,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from loguru import logger
from config.config_manager import ConfigManager
from ui.styles import StyleHelper


class SetupWizard(QDialog):
    """首次运行设置向导"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager()
        self.setWindowTitle("ACE-KILLER v2.2.2 - 首次设置")
        self.setMinimumSize(550, 400)
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 标题
        title = QLabel("欢迎使用 ACE-KILLER v2.2.2")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 步骤堆栈
        self.stack = QStackedWidget()

        # 第1页: 欢迎
        welcome_page = QWidget()
        welcome_layout = QVBoxLayout(welcome_page)
        welcome_label = QLabel(
            "ACE-KILLER 是一款 ACE 反作弊进程管理工具，可以帮助您：\n\n"
            "- 自动优化 ACE 反作弊进程，降低资源占用\n"
            "- 使用 RAM 盘重定向减少 SSD 写入损伤\n"
            "- 清理系统内存，提升游戏性能\n"
            "- 自定义进程规则，灵活控制系统资源分配\n\n"
            "点击「下一步」开始配置"
        )
        welcome_label.setWordWrap(True)
        welcome_layout.addWidget(welcome_label)
        welcome_layout.addStretch()
        self.stack.addWidget(welcome_page)

        # 第2页: 监控设置
        monitor_page = QWidget()
        monitor_layout = QVBoxLayout(monitor_page)

        monitor_group = QGroupBox("进程监控设置")
        monitor_group_layout = QVBoxLayout()

        self.monitor_check = QCheckBox("启用 ACE 弹窗监控（推荐）")
        self.monitor_check.setChecked(True)
        monitor_group_layout.addWidget(self.monitor_check)

        self.wmi_check = QCheckBox("使用 WMI 事件监控（更高效，需管理员权限）")
        self.wmi_check.setChecked(True)
        monitor_group_layout.addWidget(self.wmi_check)

        wmi_info = QLabel(
            "WMI 模式：实时接收进程创建事件，CPU 占用更低\n"
            "轮询模式：每 5 秒扫描一次进程列表，兼容性更好"
        )
        wmi_info.setWordWrap(True)
        StyleHelper.set_label_type(wmi_info, "info")
        monitor_group_layout.addWidget(wmi_info)

        monitor_group.setLayout(monitor_group_layout)
        monitor_layout.addWidget(monitor_group)
        monitor_layout.addStretch()
        self.stack.addWidget(monitor_page)

        # 第3页: RAM盘设置
        ramdisk_page = QWidget()
        ramdisk_layout = QVBoxLayout(ramdisk_page)

        ramdisk_group = QGroupBox("RAM 盘重定向")
        ramdisk_group_layout = QVBoxLayout()

        self.ramdisk_check = QCheckBox("启用 RAM 盘重定向（推荐）")
        self.ramdisk_check.setChecked(True)
        ramdisk_group_layout.addWidget(self.ramdisk_check)

        ramdisk_info = QLabel(
            "RAM 盘重定向将 ACE 反作弊的临时文件映射到内存中，\n"
            "可以有效减少 SSD 的写入磨损，延长硬盘寿命。\n\n"
            "如果安装了 ImDisk，将创建真正的内存盘；\n"
            "否则使用 Windows subst 创建虚拟驱动器。"
        )
        ramdisk_info.setWordWrap(True)
        StyleHelper.set_label_type(ramdisk_info, "info")
        ramdisk_group_layout.addWidget(ramdisk_info)

        ramdisk_group.setLayout(ramdisk_group_layout)
        ramdisk_layout.addWidget(ramdisk_group)
        ramdisk_layout.addStretch()
        self.stack.addWidget(ramdisk_page)

        # 第4页: 完成
        complete_page = QWidget()
        complete_layout = QVBoxLayout(complete_page)

        complete_label = QLabel(
            "配置完成！\n\n"
            "您可以随时在程序设置中修改这些选项。\n"
            "点击「开始使用」启动 ACE-KILLER"
        )
        complete_label.setWordWrap(True)
        complete_label.setAlignment(Qt.AlignCenter)
        complete_layout.addWidget(complete_label)
        complete_layout.addStretch()
        self.stack.addWidget(complete_page)

        layout.addWidget(self.stack)

        # 导航按钮
        nav_layout = QHBoxLayout()
        nav_layout.addStretch()

        self.back_btn = QPushButton("上一步")
        self.back_btn.clicked.connect(self.go_back)
        self.back_btn.setEnabled(False)
        nav_layout.addWidget(self.back_btn)

        self.next_btn = QPushButton("下一步")
        self.next_btn.clicked.connect(self.go_next)
        nav_layout.addWidget(self.next_btn)

        layout.addLayout(nav_layout)

        self.current_page = 0
        self.total_pages = self.stack.count()

    def go_next(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.stack.setCurrentIndex(self.current_page)
            self.back_btn.setEnabled(True)

            if self.current_page == self.total_pages - 1:
                self.next_btn.setText("开始使用")
                self._apply_settings()

    def go_back(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.stack.setCurrentIndex(self.current_page)
            self.back_btn.setEnabled(self.current_page > 0)
            self.next_btn.setText("下一步")

    def _apply_settings(self):
        """应用设置"""
        try:
            self.config.monitor_enabled = self.monitor_check.isChecked()
            self.config.use_wmi = self.wmi_check.isChecked()
            self.config.ramdisk_enabled = self.ramdisk_check.isChecked()
            self.config.first_run = False
            self.config.wizard_done = True  # v2.2.1: 标记向导完成，避免下次启动重复弹出
            self.config.save_config()
            logger.success("首次设置已保存")
        except Exception as e:
            logger.error(f"保存首次设置失败: {e}")

    def accept(self):
        self._apply_settings()
        super().accept()
