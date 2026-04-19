from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QCheckBox,
)

from styles.theme import ACCENT, BG_CARD, BG_CARD_ALT, BG_MAIN, BORDER, BORDER_LIGHT, CYAN, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY
from ui.ui_effects import apply_soft_shadow


def _section_card(title: str, subtitle: str) -> tuple[QFrame, QVBoxLayout]:
    card = QFrame()
    card.setStyleSheet(
        f"""
        QFrame {{
            background-color: {BG_CARD};
            border: 1px solid {BORDER};
            border-radius: 18px;
        }}
        QFrame:hover {{
            border: 1px solid {BORDER_LIGHT};
        }}
        """
    )
    apply_soft_shadow(card, blur_radius=26, offset_y=7, alpha=74)

    layout = QVBoxLayout(card)
    layout.setContentsMargins(22, 20, 22, 20)
    layout.setSpacing(0)

    title_lbl = QLabel(title)
    title_lbl.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
    title_lbl.setStyleSheet(f"color:{TEXT_PRIMARY}; background:transparent; border:none;")
    layout.addWidget(title_lbl)
    layout.addSpacing(6)

    subtitle_lbl = QLabel(subtitle)
    subtitle_lbl.setWordWrap(True)
    subtitle_lbl.setStyleSheet(f"color:{TEXT_SECONDARY}; background:transparent; border:none;")
    layout.addWidget(subtitle_lbl)
    layout.addSpacing(18)
    return card, layout


def _field_label(text: str) -> QLabel:
    widget = QLabel(text)
    widget.setStyleSheet(f"color:{TEXT_MUTED}; background:transparent; border:none;")
    return widget


def _style_spinbox(widget: QSpinBox):
    widget.setButtonSymbols(QSpinBox.ButtonSymbols.PlusMinus)
    widget.setStyleSheet(
        f"""
        QSpinBox {{
            background-color: {BG_CARD_ALT};
            color: {TEXT_PRIMARY};
            border: 1px solid {BORDER};
            border-radius: 10px;
            padding: 6px 10px;
            min-height: 34px;
        }}
        QSpinBox::up-button, QSpinBox::down-button {{
            width: 22px;
            border: none;
            background: transparent;
        }}
        """
    )


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color:{BG_MAIN};")
        self._engine = None
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background:transparent; border:none; }")
        outer.addWidget(scroll)

        container = QWidget()
        container.setStyleSheet(f"background-color:{BG_MAIN};")
        scroll.setWidget(container)

        root = QVBoxLayout(container)
        root.setContentsMargins(28, 24, 28, 28)
        root.setSpacing(18)

        hero = QFrame()
        hero.setStyleSheet(
            f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f172a, stop:0.4 #131d35, stop:1 #0a1122);
                border: 1px solid #1e2d45;
                border-radius: 22px;
            }}
            """
        )
        apply_soft_shadow(hero, blur_radius=30, offset_y=8, alpha=84)
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(24, 22, 24, 22)
        hero_layout.setSpacing(24)

        left = QVBoxLayout()
        left.setSpacing(0)

        badge = QLabel("SYSTEM SETTINGS")
        badge.setFixedWidth(136)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            f"""
            color: {CYAN};
            background-color: {CYAN}22;
            border: 1px solid {CYAN}55;
            border-radius: 12px;
            padding: 4px 10px;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1px;
            """
        )
        left.addWidget(badge, alignment=Qt.AlignmentFlag.AlignLeft)
        left.addSpacing(14)

        title = QLabel("Settings")
        title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{TEXT_PRIMARY}; background:transparent; border:none;")
        left.addWidget(title)
        left.addSpacing(8)

        sub = QLabel(
            "Tune the tracker, define quiet hours, and teach Focus.io how to classify your tools. Focus Mode controls now live on their own page."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color:{TEXT_SECONDARY}; background:transparent; border:none;")
        left.addWidget(sub)
        hero_layout.addLayout(left, 1)

        open_focus = QPushButton("Open Focus Mode")
        open_focus.setCursor(Qt.CursorShape.PointingHandCursor)
        open_focus.setFixedHeight(44)
        open_focus.setStyleSheet(
            f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:1 #a855f7);
                color: white;
                border: none;
                border-radius: 13px;
                padding: 0 20px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #818cf8, stop:1 #c084fc);
            }}
            """
        )
        open_focus.clicked.connect(self._open_focus_mode)
        hero_layout.addWidget(open_focus, alignment=Qt.AlignmentFlag.AlignCenter)
        root.addWidget(hero)

        tracking_card, tracking_layout = _section_card(
            "Tracking Behavior",
            "Adjust how quickly inactivity becomes idle time in analytics and focus sessions.",
        )
        tracking_grid = QGridLayout()
        tracking_grid.setHorizontalSpacing(12)
        tracking_grid.setVerticalSpacing(12)

        tracking_grid.addWidget(_field_label("Idle threshold"), 0, 0)
        self.idle_seconds = QSpinBox()
        self.idle_seconds.setRange(30, 3600)
        self.idle_seconds.setSuffix(" sec")
        _style_spinbox(self.idle_seconds)
        tracking_grid.addWidget(self.idle_seconds, 0, 1)
        tracking_layout.addLayout(tracking_grid)
        root.addWidget(tracking_card)

        quiet_card, quiet_layout = _section_card(
            "Quiet Hours",
            "Pause distraction overlays during off-hours so Focus.io does not nudge you when you are intentionally away from work.",
        )
        self.quiet_enabled = QCheckBox("Enable quiet hours")
        self.quiet_enabled.setStyleSheet(f"color:{TEXT_PRIMARY};")
        quiet_layout.addWidget(self.quiet_enabled)
        quiet_layout.addSpacing(14)

        quiet_grid = QGridLayout()
        quiet_grid.setHorizontalSpacing(12)
        quiet_grid.setVerticalSpacing(12)

        quiet_grid.addWidget(_field_label("From hour"), 0, 0)
        self.quiet_start = QSpinBox()
        self.quiet_start.setRange(0, 23)
        self.quiet_start.setSuffix(":00")
        _style_spinbox(self.quiet_start)
        quiet_grid.addWidget(self.quiet_start, 0, 1)

        quiet_grid.addWidget(_field_label("To hour"), 1, 0)
        self.quiet_end = QSpinBox()
        self.quiet_end.setRange(0, 23)
        self.quiet_end.setSuffix(":00")
        _style_spinbox(self.quiet_end)
        quiet_grid.addWidget(self.quiet_end, 1, 1)
        quiet_layout.addLayout(quiet_grid)
        root.addWidget(quiet_card)

        rules_card, rules_layout = _section_card(
            "Classifier Overrides",
            "Teach the classifier by mapping domains to categories. Use one rule per line with the format domain=category.",
        )
        example = QLabel("Example: youtube.com=entertainment\narxiv.org=learning")
        example.setStyleSheet(f"color:{TEXT_MUTED}; background:transparent; border:none;")
        rules_layout.addWidget(example)
        rules_layout.addSpacing(12)

        self.rules_edit = QPlainTextEdit()
        self.rules_edit.setPlaceholderText("youtube.com=entertainment\narxiv.org=learning")
        self.rules_edit.setStyleSheet(
            f"""
            QPlainTextEdit {{
                background-color: {BG_CARD_ALT};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER};
                border-radius: 12px;
                padding: 12px;
            }}
            """
        )
        self.rules_edit.setFixedHeight(150)
        rules_layout.addWidget(self.rules_edit)
        root.addWidget(rules_card)

        export_card, export_layout = _section_card(
            "Data & Export",
            "Create a readable JSON backup of your tracked sessions, tasks, and saved settings.",
        )
        self.export_btn = QPushButton("Export tracking data (JSON)")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.setFixedHeight(40)
        self.export_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {ACCENT};
                border: 1px solid {ACCENT};
                border-radius: 12px;
                padding: 0 16px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {ACCENT}22;
            }}
            """
        )
        self.export_btn.clicked.connect(self._export_data)
        export_layout.addWidget(self.export_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        root.addWidget(export_card)

        root.addStretch()

        actions = QHBoxLayout()
        actions.addStretch()
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setFixedHeight(44)
        self.save_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:1 #a855f7);
                color: white;
                border: none;
                border-radius: 13px;
                padding: 0 22px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #818cf8, stop:1 #c084fc);
            }}
            """
        )
        self.save_btn.clicked.connect(self._save_settings)
        actions.addWidget(self.save_btn)
        root.addLayout(actions)

    def set_engine(self, engine):
        self._engine = engine
        if not engine:
            return
        try:
            engine.settings_changed.connect(self._load_settings_to_ui)
        except TypeError:
            pass
        self._load_settings_to_ui(engine.get_settings())

    def _load_settings_to_ui(self, settings: dict):
        self.idle_seconds.setValue(int(settings.get("idle_threshold_seconds", 300)))
        self.quiet_enabled.setChecked(bool(settings.get("quiet_hours_enabled", False)))
        self.quiet_start.setValue(int(settings.get("quiet_start_hour", 22)))
        self.quiet_end.setValue(int(settings.get("quiet_end_hour", 7)))

        rules = settings.get("manual_category_rules") or {}
        if isinstance(rules, dict):
            lines = [f"{pattern}={category}" for pattern, category in rules.items()]
            self.rules_edit.setPlainText("\n".join(lines))

    def _save_settings(self):
        if not self._engine:
            QMessageBox.warning(self, "Settings", "Engine is not ready yet.")
            return

        manual_rules = {}
        for raw_line in self.rules_edit.toPlainText().splitlines():
            line = raw_line.strip()
            if not line or "=" not in line:
                continue
            pattern, category = line.split("=", 1)
            manual_rules[pattern.strip().lower()] = category.strip().lower()

        payload = {
            "idle_threshold_seconds": self.idle_seconds.value(),
            "quiet_hours_enabled": self.quiet_enabled.isChecked(),
            "quiet_start_hour": self.quiet_start.value(),
            "quiet_end_hour": self.quiet_end.value(),
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
        except Exception as exc:
            QMessageBox.critical(self, "Export Data", f"Failed to export data:\n{exc}")

    def _open_focus_mode(self):
        main_win = self.window()
        if hasattr(main_win, "_sidebar"):
            main_win._sidebar.set_active_index(3)
