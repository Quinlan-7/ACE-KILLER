#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
规则编辑对话框 v2.0
"""

from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QCheckBox, QGroupBox, QFormLayout,
    QTextEdit, QDialogButtonBox, QScrollArea,
)
from PySide6.QtCore import Qt

from core.rule_engine import ProcessRule


class RuleDialog(QDialog):
    """进程规则编辑对话框"""

    def __init__(self, parent=None, rule: ProcessRule = None):
        super().__init__(parent)
        self.rule = rule
        self.setWindowTitle("编辑规则" if rule else "添加规则")
        self.setMinimumWidth(450)
        self.setup_ui()

        if rule:
            self._load_rule(rule)

    def setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入规则名称（如: 限制SGuard64）")
        form.addRow("规则名称:", self.name_edit)

        self.pattern_edit = QLineEdit()
        self.pattern_edit.setPlaceholderText("如: SGuard64.exe, *.exe, ^SGuard.*")
        form.addRow("进程匹配:", self.pattern_edit)

        self.match_combo = QComboBox()
        self.match_combo.addItems(["exact - 精确匹配", "wildcard - 通配符", "regex - 正则"])
        form.addRow("匹配方式:", self.match_combo)

        # 动作分组
        actions_group = QGroupBox("限制动作")
        actions_layout = QVBoxLayout()

        self.action_io = QCheckBox("设置 IO 优先级为最低")
        actions_layout.addWidget(self.action_io)

        self.action_cpu_priority = QCheckBox("设置 CPU 优先级为 IDLE")
        actions_layout.addWidget(self.action_cpu_priority)

        self.action_cpu_affinity = QCheckBox("限制 CPU 核心数为 1")
        actions_layout.addWidget(self.action_cpu_affinity)

        self.action_power = QCheckBox("启用效能节流模式")
        actions_layout.addWidget(self.action_power)

        self.action_terminate = QCheckBox("终止进程（谨慎使用）")
        actions_layout.addWidget(self.action_terminate)

        self.action_ramdisk = QCheckBox("重定向临时目录到 RAM 盘")
        actions_layout.addWidget(self.action_ramdisk)

        actions_group.setLayout(actions_layout)
        form.addRow(actions_group)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("规则描述（可选）")
        self.desc_edit.setMaximumHeight(60)
        form.addRow("描述:", self.desc_edit)

        layout.addLayout(form)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_rule(self, rule: ProcessRule):
        self.name_edit.setText(rule.name)
        self.pattern_edit.setText(rule.process_pattern)

        match_idx = {"exact": 0, "wildcard": 1, "regex": 2}
        self.match_combo.setCurrentIndex(
            match_idx.get(rule.match_type, 0)
        )

        for action in rule.actions:
            atype = action.get("type", "")
            if atype == "io_priority":
                self.action_io.setChecked(True)
            elif atype == "cpu_priority":
                self.action_cpu_priority.setChecked(True)
            elif atype == "cpu_affinity":
                self.action_cpu_affinity.setChecked(True)
            elif atype == "power_throttling":
                self.action_power.setChecked(True)
            elif atype == "terminate":
                self.action_terminate.setChecked(True)
            elif atype == "ramdisk_redirect":
                self.action_ramdisk.setChecked(True)

        self.desc_edit.setPlainText(rule.description)
        self.name_edit.setReadOnly(True)

    def validate_and_accept(self):
        name = self.name_edit.text().strip()
        pattern = self.pattern_edit.text().strip()

        if not name:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "验证失败", "请输入规则名称")
            return

        if not pattern:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "验证失败", "请输入进程匹配模式")
            return

        self.accept()

    def get_rule(self) -> ProcessRule:
        """获取编辑后的规则"""
        if not self.name_edit.text().strip():
            return None

        match_text = self.match_combo.currentText()
        match_type = match_text.split(" - ")[0] if " - " in match_text else match_text

        actions = []
        if self.action_io.isChecked():
            actions.append({"type": "io_priority", "value": 0})
        if self.action_cpu_priority.isChecked():
            actions.append({"type": "cpu_priority", "value": "IDLE"})
        if self.action_cpu_affinity.isChecked():
            actions.append({"type": "cpu_affinity", "value": 1})
        if self.action_power.isChecked():
            actions.append({"type": "power_throttling", "value": True})
        if self.action_terminate.isChecked():
            actions.append({"type": "terminate", "value": True})
        if self.action_ramdisk.isChecked():
            actions.append({"type": "ramdisk_redirect", "value": True})

        return ProcessRule(
            name=self.name_edit.text().strip(),
            process_pattern=self.pattern_edit.text().strip(),
            match_type=match_type,
            actions=actions,
            enabled=True,
            created_at=datetime.now().isoformat(),
            description=self.desc_edit.toPlainText().strip(),
        )
