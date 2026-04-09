from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QCheckBox,
    QSpinBox,
    QPushButton,
    QGridLayout,
    QMessageBox,
    QPlainTextEdit,
    QFileDialog,
)

from styles.theme import BG_MAIN, BG_CARD, BORDER, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED
from ui.ui_effects import apply_soft_shadow


def _section_card(title: str, subtitle: str) -> tuple[QFrame, QVBoxLayout]:
    card = QFrame()
    card.setStyleSheet(
        f"""
        QFrame {{
            background-color: {BG_CARD};
            border: 1px solid {BORDER};
            border-radius: 14px;
        }}
        """
    )
    apply_soft_shadow(card, blur_radius=24, offset_y=6, alpha=64)

    layout = QVBoxLayout(card)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(10)

    t = QLabel(title)
    t.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    t.setStyleSheet(f"color:{TEXT_PRIMARY}; background:transparent; border:none;")
    layout.addWidget(t)

    s = QLabel(subtitle)
    s.setWordWrap(True)
    s.setStyleSheet(f"color:{TEXT_SECONDARY}; background:transparent; border:none;")
    layout.addWidget(s)
    return card, layout


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color:{BG_MAIN};")
        self._engine = None
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 28)
        root.setSpacing(16)

        title = QLabel("Settings")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{TEXT_PRIMARY}; background:transparent; border:none;")
        root.addWidget(title)

        sub = QLabel("Control attention alerts, thresholds, quiet hours, and tracking behavior.")
        sub.setStyleSheet(f"color:{TEXT_SECONDARY}; background:transparent; border:none;")
        root.addWidget(sub)

        # Alert settings
        alert_card, alert_layout = _section_card(
            "Attention Alerts",
            "Configure when and how the app should nudge you back to focus.",
        )
        self.alerts_enabled = QCheckBox("Enable attention alerts")
        self.alerts_enabled.setChecked(True)
        alert_layout.addWidget(self.alerts_enabled)

        categories_row = QHBoxLayout()
        categories_row.setSpacing(18)
        self.cat_entertainment = QCheckBox("Entertainment")
        self.cat_browsing = QCheckBox("Browsing")
        self.cat_communication = QCheckBox("Communication")
        self.cat_entertainment.setChecked(True)
        self.cat_browsing.setChecked(True)
        categories_row.addWidget(self.cat_entertainment)
        categories_row.addWidget(self.cat_browsing)
        categories_row.addWidget(self.cat_communication)
        categories_row.addStretch()
        alert_layout.addLayout(categories_row)

        threshold_grid = QGridLayout()
        threshold_grid.setHorizontalSpacing(10)
        threshold_grid.setVerticalSpacing(8)

        threshold_grid.addWidget(self._label("Warn after (minutes)"), 0, 0)
        self.warn_minutes = QSpinBox()
        self.warn_minutes.setRange(1, 240)
        self.warn_minutes.setValue(10)
        self.warn_minutes.setSuffix(" min")
        threshold_grid.addWidget(self.warn_minutes, 0, 1)

        threshold_grid.addWidget(self._label("Alert cooldown"), 1, 0)
        self.cooldown_minutes = QSpinBox()
        self.cooldown_minutes.setRange(1, 720)
        self.cooldown_minutes.setValue(30)
        self.cooldown_minutes.setSuffix(" min")
        threshold_grid.addWidget(self.cooldown_minutes, 1, 1)
        alert_layout.addLayout(threshold_grid)
        root.addWidget(alert_card)

        # Quiet hours
        quiet_card, quiet_layout = _section_card(
            "Quiet Hours",
            "Silence attention overlays during your off-hours.",
        )
        self.quiet_enabled = QCheckBox("Enable quiet hours")
        quiet_layout.addWidget(self.quiet_enabled)

        quiet_grid = QGridLayout()
        quiet_grid.setHorizontalSpacing(10)
        quiet_grid.setVerticalSpacing(8)
        quiet_grid.addWidget(self._label("From hour"), 0, 0)
        self.quiet_start = QSpinBox()
        self.quiet_start.setRange(0, 23)
        self.quiet_start.setValue(22)
        self.quiet_start.setSuffix(":00")
        quiet_grid.addWidget(self.quiet_start, 0, 1)

        quiet_grid.addWidget(self._label("To hour"), 1, 0)
        self.quiet_end = QSpinBox()
        self.quiet_end.setRange(0, 23)
        self.quiet_end.setValue(7)
        self.quiet_end.setSuffix(":00")
        quiet_grid.addWidget(self.quiet_end, 1, 1)
        quiet_layout.addLayout(quiet_grid)
        root.addWidget(quiet_card)

        # Tracker behavior
        tracker_card, tracker_layout = _section_card(
            "Tracking",
            "Tune how quickly inactivity is treated as idle.",
        )
        tracker_grid = QGridLayout()
        tracker_grid.setHorizontalSpacing(10)
        tracker_grid.setVerticalSpacing(8)
        tracker_grid.addWidget(self._label("Idle threshold"), 0, 0)
        self.idle_seconds = QSpinBox()
        self.idle_seconds.setRange(30, 3600)
        self.idle_seconds.setValue(300)
        self.idle_seconds.setSuffix(" sec")
        tracker_grid.addWidget(self.idle_seconds, 0, 1)
        tracker_layout.addLayout(tracker_grid)
        root.addWidget(tracker_card)

        # Manual category rules
        rules_card, rules_layout = _section_card(
            "Manual Category Rules",
            "Override the classifier by mapping domains to categories. "
            "Example:  'youtube.com=entertainment', 'arxiv.org=learning'. One rule per line.",
        )
        self.rules_edit = QPlainTextEdit()
        self.rules_edit.setPlaceholderText("youtube.com=entertainment\narxiv.org=learning")
        self.rules_edit.setStyleSheet(
            f"background-color: {BG_MAIN}; color:{TEXT_PRIMARY}; border-radius:8px; border:1px solid {BORDER};"
        )
        self.rules_edit.setFixedHeight(120)
        rules_layout.addWidget(self.rules_edit)
        root.addWidget(rules_card)

        # Export data
        export_card, export_layout = _section_card(
            "Data Export",
            "Download all your tracked data as a readable JSON text file.",
        )
        self.export_btn = QPushButton("Export tracking data (JSON)")
        self.export_btn.setFixedHeight(34)
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {ACCENT};
                border: 1px solid {ACCENT};
                border-radius: 8px;
                padding: 0 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {ACCENT}22;
            }}
            """
        )
        self.export_btn.clicked.connect(self._export_data)
        export_layout.addWidget(self.export_btn)
        root.addWidget(export_card)

        root.addStretch()

        action_row = QHBoxLayout()
        action_row.addStretch()
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setFixedHeight(38)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {ACCENT};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 0 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #4f46e5;
            }}
            """
        )
        self.save_btn.clicked.connect(self._save_settings)
        action_row.addWidget(self.save_btn)
        root.addLayout(action_row)

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{TEXT_MUTED}; background:transparent; border:none;")
        return lbl

    def set_engine(self, engine):
        self._engine = engine
        if not engine:
            return
        self._load_settings_to_ui(engine.get_settings())

    def _load_settings_to_ui(self, settings: dict):
        self.alerts_enabled.setChecked(bool(settings.get("alerts_enabled", True)))
        categories = set(settings.get("warning_categories", ["entertainment", "browsing"]))
        self.cat_entertainment.setChecked("entertainment" in categories)
        self.cat_browsing.setChecked("browsing" in categories)
        self.cat_communication.setChecked("communication" in categories)

        self.warn_minutes.setValue(int(settings.get("warning_threshold_minutes", 10)))
        self.cooldown_minutes.setValue(int(settings.get("warning_cooldown_minutes", 30)))
        self.quiet_enabled.setChecked(bool(settings.get("quiet_hours_enabled", False)))
        self.quiet_start.setValue(int(settings.get("quiet_start_hour", 22)))
        self.quiet_end.setValue(int(settings.get("quiet_end_hour", 7)))
        self.idle_seconds.setValue(int(settings.get("idle_threshold_seconds", 300)))

        # Manual rules: dict pattern->category
        rules = settings.get("manual_category_rules") or {}
        if isinstance(rules, dict):
            lines = [f"{pat}={cat}" for pat, cat in rules.items()]
            self.rules_edit.setPlainText("\n".join(lines))

    def _save_settings(self):
        if not self._engine:
            QMessageBox.warning(self, "Settings", "Engine is not ready yet.")
            return

        categories = []
        if self.cat_entertainment.isChecked():
            categories.append("entertainment")
        if self.cat_browsing.isChecked():
            categories.append("browsing")
        if self.cat_communication.isChecked():
            categories.append("communication")

        if not categories:
            QMessageBox.warning(
                self,
                "Settings",
                "Please select at least one warning category.",
            )
            return

        # Parse rules text → dict
        manual_rules = {}
        for raw_line in self.rules_edit.toPlainText().splitlines():
            line = raw_line.strip()
            if not line or "=" not in line:
                continue
            pat, cat = line.split("=", 1)
            manual_rules[pat.strip().lower()] = cat.strip().lower()

        payload = {
            "alerts_enabled": self.alerts_enabled.isChecked(),
            "warning_categories": categories,
            "warning_threshold_minutes": self.warn_minutes.value(),
            "warning_cooldown_minutes": self.cooldown_minutes.value(),
            "quiet_hours_enabled": self.quiet_enabled.isChecked(),
            "quiet_start_hour": self.quiet_start.value(),
            "quiet_end_hour": self.quiet_end.value(),
            "idle_threshold_seconds": self.idle_seconds.value(),
            "manual_category_rules": manual_rules,
        }
        self._engine.update_settings(payload)
        QMessageBox.information(self, "Settings", "Settings saved successfully.")

    def _export_data(self):
        if not self._engine:
            QMessageBox.warning(self, "Export Data", "Engine is not ready yet.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export tracking data (JSON)",
            "tracking_export.json",
            "JSON Files (*.json);;Text Files (*.txt)",
        )
        if not path:
            return
        try:
            self._engine.db_manager.export_as_json(path)
            QMessageBox.information(self, "Export Data", f"Data exported as JSON to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Data", f"Failed to export data:\n{e}")
