#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
场景预设编辑对话框 v2.0
"""

from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QCheckBox, QGroupBox, QFormLayout,
    QTextEdit, QDialogButtonBox, QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt

from core.profile_manager import GameProfile
from core.rule_engine import get_rule_engine


class ProfileDialog(QDialog):
    """场景预设编辑对话框"""

    def __init__(self, parent=None, profile: GameProfile = None):
        super().__init__(parent)
        self.profile = profile
        self.rule_engine = get_rule_engine()
        self.setWindowTitle("编辑预设" if profile else "添加预设")
        self.setMinimumWidth(500)
        self.setup_ui()

        if profile:
            self._load_profile(profile)

    def setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("如: 无畏契约模式")
        form.addRow("预设名称:", self.name_edit)

        self.trigger_edit = QLineEdit()
        self.trigger_edit.setPlaceholderText("如: VALORANT.exe")
        form.addRow("触发进程:", self.trigger_edit)

        self.ramdisk_check = QCheckBox("启用 RAM 盘重定向")
        form.addRow("", self.ramdisk_check)

        self.memory_check = QCheckBox("激活时清理内存")
        form.addRow("", self.memory_check)

        # 关联规则选择
        rules_group = QGroupBox("关联的进程规则")
        rules_layout = QVBoxLayout()

        self.rules_list = QListWidget()
        self._populate_rules_list()
        rules_layout.addWidget(self.rules_list)

        rules_group.setLayout(rules_layout)
        form.addRow(rules_group)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("预设描述（可选）")
        self.desc_edit.setMaximumHeight(60)
        form.addRow("描述:", self.desc_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate_rules_list(self):
        """填充可用规则列表"""
        self.rules_list.clear()
        for rule in self.rule_engine.list_rules():
            item = QListWidgetItem(rule.name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.rules_list.addItem(item)

    def _load_profile(self, profile: GameProfile):
        self.name_edit.setText(profile.name)
        self.trigger_edit.setText(profile.trigger_process)
        self.ramdisk_check.setChecked(profile.ramdisk_enabled)
        self.memory_check.setChecked(profile.memory_clean)
        self.desc_edit.setPlainText(profile.description)
        self.name_edit.setReadOnly(True)

        # 勾选关联的规则
        for i in range(self.rules_list.count()):
            item = self.rules_list.item(i)
            if item.text() in profile.rules:
                item.setCheckState(Qt.Checked)

    def validate_and_accept(self):
        name = self.name_edit.text().strip()
        if not name:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "验证失败", "请输入预设名称")
            return
        self.accept()

    def get_profile(self) -> GameProfile:
        if not self.name_edit.text().strip():
            return None

        # 获取选中的规则
        selected_rules = []
        for i in range(self.rules_list.count()):
            item = self.rules_list.item(i)
            if item.checkState() == Qt.Checked:
                selected_rules.append(item.text())

        return GameProfile(
            name=self.name_edit.text().strip(),
            description=self.desc_edit.toPlainText().strip(),
            trigger_process=self.trigger_edit.text().strip(),
            rules=selected_rules,
            ramdisk_enabled=self.ramdisk_check.isChecked(),
            memory_clean=self.memory_check.isChecked(),
            io_priority_processes=[],
            enabled=True,
            created_at=datetime.now().isoformat(),
        )
