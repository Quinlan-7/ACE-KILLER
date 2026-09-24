#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
场景预设标签页 v2.0
游戏场景预设管理
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QGroupBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from loguru import logger
from core.profile_manager import get_profile_manager, GameProfile
from ui.styles import StyleHelper
from ui.signal_bus import get_signal_bus


class ProfilesTab(QWidget):
    """场景预设管理标签页"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.profile_manager = get_profile_manager()
        self.signal_bus = get_signal_bus()
        self.setup_ui()
        self.refresh_profiles()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 说明
        info = QLabel(
            "场景预设可以让游戏启动时自动应用一组优化策略。\n"
            "设置触发进程后，检测到该进程启动就会自动激活对应的预设。"
        )
        info.setWordWrap(True)
        StyleHelper.set_label_type(info, "info")
        layout.addWidget(info)

        # 按钮区域
        btn_layout = QHBoxLayout()

        self.add_btn = QPushButton("添加预设")
        self.add_btn.clicked.connect(self.add_profile)
        btn_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("编辑预设")
        self.edit_btn.clicked.connect(self.edit_profile)
        btn_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("删除预设")
        self.delete_btn.clicked.connect(self.delete_profile)
        btn_layout.addWidget(self.delete_btn)

        btn_layout.addStretch()

        self.activate_btn = QPushButton("激活预设")
        self.activate_btn.clicked.connect(self.activate_profile)
        self.activate_btn.setEnabled(False)
        btn_layout.addWidget(self.activate_btn)

        self.deactivate_btn = QPushButton("停用预设")
        self.deactivate_btn.clicked.connect(self.deactivate_profile)
        self.deactivate_btn.setEnabled(False)
        btn_layout.addWidget(self.deactivate_btn)

        layout.addLayout(btn_layout)

        # 当前激活状态
        self.status_label = QLabel("当前预设: 无")
        StyleHelper.set_label_type(self.status_label, "info")
        layout.addWidget(self.status_label)

        # 预设表格
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "启用", "预设名称", "触发进程", "关联规则", "RAM盘", "描述"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # 更新激活状态
        self._update_active_status()

    def _update_active_status(self):
        active = self.profile_manager.active_profile
        if active:
            self.status_label.setText(
                f"当前预设: {active.name} (运行中)"
            )
            StyleHelper.set_label_type(self.status_label, "success")
            self.activate_btn.setEnabled(False)
            self.deactivate_btn.setEnabled(True)
        else:
            self.status_label.setText("当前预设: 无")
            StyleHelper.set_label_type(self.status_label, "info")
            self.activate_btn.setEnabled(True)
            self.deactivate_btn.setEnabled(False)

    def refresh_profiles(self):
        """刷新预设列表"""
        profiles = self.profile_manager.list_profiles()
        self.table.setRowCount(len(profiles))

        for i, profile in enumerate(profiles):
            enabled_item = QTableWidgetItem("是" if profile.enabled else "否")
            enabled_item.setTextAlignment(Qt.AlignCenter)
            if profile.enabled:
                enabled_item.setForeground(QColor("#52c41a"))
            else:
                enabled_item.setForeground(QColor("#ff4d4f"))
            self.table.setItem(i, 0, enabled_item)

            self.table.setItem(i, 1, QTableWidgetItem(profile.name))
            self.table.setItem(
                i, 2, QTableWidgetItem(profile.trigger_process)
            )
            self.table.setItem(
                i, 3,
                QTableWidgetItem(", ".join(profile.rules) if profile.rules else "无")
            )
            self.table.setItem(
                i, 4,
                QTableWidgetItem("是" if profile.ramdisk_enabled else "否")
            )
            self.table.setItem(i, 5, QTableWidgetItem(profile.description))

        self.table.resizeColumnsToContents()
        self._update_active_status()

    def add_profile(self):
        from ui.dialogs.profile_dialog import ProfileDialog
        dialog = ProfileDialog(self)
        if dialog.exec_():
            profile = dialog.get_profile()
            if profile:
                self.profile_manager.add_profile(profile)
                self.refresh_profiles()
                self.signal_bus.config_changed.emit("profiles")
                logger.success(f"已添加预设: {profile.name}")

    def edit_profile(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选择一个预设")
            return

        name = self.table.item(row, 1).text()
        profile = self.profile_manager.get_profile(name)
        if not profile:
            QMessageBox.warning(self, "错误", "未找到该预设")
            return

        from ui.dialogs.profile_dialog import ProfileDialog
        dialog = ProfileDialog(self, profile)
        if dialog.exec_():
            updated = dialog.get_profile()
            if updated:
                self.profile_manager.update_profile(updated)
                self.refresh_profiles()
                self.signal_bus.config_changed.emit("profiles")
                logger.success(f"已更新预设: {updated.name}")

    def delete_profile(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选择一个预设")
            return

        name = self.table.item(row, 1).text()
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除预设「{name}」吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.profile_manager.remove_profile(name)
            self.refresh_profiles()
            self.signal_bus.config_changed.emit("profiles")
            logger.success(f"已删除预设: {name}")

    def activate_profile(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选择一个预设")
            return

        name = self.table.item(row, 1).text()
        if self.profile_manager.activate_profile(name):
            self.refresh_profiles()
            self.signal_bus.profile_activated.emit(name)
            QMessageBox.information(self, "成功", f"已激活预设: {name}")

    def deactivate_profile(self):
        if self.profile_manager.deactivate_profile():
            self.refresh_profiles()
            self.signal_bus.profile_deactivated.emit()
            QMessageBox.information(self, "成功", "已停用当前预设")
