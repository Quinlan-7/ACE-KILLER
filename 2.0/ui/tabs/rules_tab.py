#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
规则引擎标签页 v2.0
自定义进程规则管理
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QGroupBox,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from loguru import logger
from core.rule_engine import get_rule_engine, ProcessRule
from ui.styles import StyleHelper
from ui.signal_bus import get_signal_bus


class RulesTab(QWidget):
    """进程规则管理标签页"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rule_engine = get_rule_engine()
        self.signal_bus = get_signal_bus()
        self.setup_ui()
        self.refresh_rules()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 说明
        info = QLabel(
            "自定义进程规则可以在进程启动时自动应用限制策略。\n"
            "支持按进程名精确匹配、通配符和正则表达式。"
        )
        info.setWordWrap(True)
        StyleHelper.set_label_type(info, "info")
        layout.addWidget(info)

        # 按钮区域
        btn_layout = QHBoxLayout()

        self.add_btn = QPushButton("添加规则")
        self.add_btn.clicked.connect(self.add_rule)
        btn_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("编辑规则")
        self.edit_btn.clicked.connect(self.edit_rule)
        btn_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("删除规则")
        self.delete_btn.clicked.connect(self.delete_rule)
        btn_layout.addWidget(self.delete_btn)

        btn_layout.addStretch()

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_rules)
        btn_layout.addWidget(self.refresh_btn)

        layout.addLayout(btn_layout)

        # 规则表格
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "启用", "规则名称", "进程匹配", "匹配方式", "动作", "描述"
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

    def refresh_rules(self):
        """刷新规则列表"""
        rules = self.rule_engine.list_rules()
        self.table.setRowCount(len(rules))

        for i, rule in enumerate(rules):
            # 启用状态
            enabled_item = QTableWidgetItem("是" if rule.enabled else "否")
            enabled_item.setTextAlignment(Qt.AlignCenter)
            if rule.enabled:
                enabled_item.setForeground(QColor("#52c41a"))
            else:
                enabled_item.setForeground(QColor("#ff4d4f"))
            self.table.setItem(i, 0, enabled_item)

            # 规则名称
            self.table.setItem(i, 1, QTableWidgetItem(rule.name))
            self.table.setItem(i, 2, QTableWidgetItem(rule.process_pattern))

            # 匹配方式
            match_display = {
                "exact": "精确", "wildcard": "通配符", "regex": "正则"
            }
            self.table.setItem(
                i, 3,
                QTableWidgetItem(match_display.get(rule.match_type, rule.match_type))
            )

            # 动作摘要
            action_summary = ", ".join(
                a.get("type", "") for a in rule.actions
            ) if rule.actions else "无"
            self.table.setItem(i, 4, QTableWidgetItem(action_summary))

            # 描述
            self.table.setItem(i, 5, QTableWidgetItem(rule.description))

        self.table.resizeColumnsToContents()

    def add_rule(self):
        """添加新规则"""
        from ui.dialogs.rule_dialog import RuleDialog
        dialog = RuleDialog(self)
        if dialog.exec_():
            rule = dialog.get_rule()
            if rule:
                self.rule_engine.add_rule(rule)
                self.refresh_rules()
                self.signal_bus.config_changed.emit("rules")
                logger.success(f"已添加规则: {rule.name}")

    def edit_rule(self):
        """编辑选中的规则"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选择一条规则")
            return

        name = self.table.item(row, 1).text()
        rule = self.rule_engine.get_rule(name)
        if not rule:
            QMessageBox.warning(self, "错误", "未找到该规则")
            return

        from ui.dialogs.rule_dialog import RuleDialog
        dialog = RuleDialog(self, rule)
        if dialog.exec_():
            updated = dialog.get_rule()
            if updated:
                self.rule_engine.update_rule(updated)
                self.refresh_rules()
                self.signal_bus.config_changed.emit("rules")
                logger.success(f"已更新规则: {updated.name}")

    def delete_rule(self):
        """删除选中的规则"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选择一条规则")
            return

        name = self.table.item(row, 1).text()
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除规则「{name}」吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.rule_engine.remove_rule(name)
            self.refresh_rules()
            self.signal_bus.config_changed.emit("rules")
            logger.success(f"已删除规则: {name}")
