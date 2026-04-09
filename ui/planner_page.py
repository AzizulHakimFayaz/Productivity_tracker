from __future__ import annotations

import datetime

from PyQt6.QtCore import Qt, QDateTime, QDate, QEvent, QPoint
from PyQt6.QtGui import QFont, QTextCharFormat, QColor, QPainter, QPen, QBrush
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QCalendarWidget,
    QLineEdit,
    QTextEdit,
    QDateTimeEdit,
    QComboBox,
    QSpinBox,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QSizePolicy,
    QTableView,
)

from styles.theme import BG_MAIN, BG_CARD, BG_CARD_ALT, BORDER, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED
from ui.ui_effects import apply_soft_shadow


class PlannerCalendarWidget(QCalendarWidget):
    """
    Calendar with custom day marker rendering (productive/entertainment/mixed).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._day_markers = {}

    def set_day_markers(self, markers: dict):
        self._day_markers = markers or {}
        # QCalendarWidget does not expose viewport(); refresh via calendar API.
        self.updateCells()

    def paintCell(self, painter: QPainter, rect, date: QDate):
        super().paintCell(painter, rect, date)
        key = date.toPyDate().isoformat()
        info = self._day_markers.get(key)
        if not info:
            return

        tag = info.get("tag", "mixed")
        if tag == "productive":
            color = QColor("#33d8b1")
        elif tag == "entertainment":
            color = QColor("#ff6b6b")
        else:
            color = QColor("#60a5fa")

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_rect = rect.adjusted(5, 5, -5, -5)
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
        painter.setPen(QPen(color, 1.7))
        painter.drawRoundedRect(draw_rect, 6, 6)
        painter.restore()


class _RatioRing(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0
        self.setFixedSize(62, 62)

    def set_value(self, value: int):
        self.value = max(0, min(100, int(value)))
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(5, 5, -5, -5)
        # Track
        p.setPen(QPen(QColor("#2f4262"), 7))
        p.drawArc(rect, 0, 360 * 16)
        # Progress (start from top)
        p.setPen(QPen(QColor("#31d5b4"), 7))
        span = int(360 * 16 * (self.value / 100.0))
        p.drawArc(rect, 90 * 16, -span)
        # Center text
        p.setPen(QColor("#dff8ff"))
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f"{self.value}%")
        p.end()


def _card() -> QFrame:
    c = QFrame()
    c.setStyleSheet(
        f"""
        QFrame {{
            background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #1b2740, stop:1 #17233a);
            border: 1px solid #2a3a56;
            border-radius: 14px;
        }}
        QLabel {{ border:none; background:transparent; }}
        """
    )
    apply_soft_shadow(c, blur_radius=24, offset_y=6, alpha=66)
    return c


def _glass_styles() -> str:
    return f"""
        QLineEdit, QTextEdit, QDateTimeEdit, QComboBox, QSpinBox {{
            background: #111d34;
            color:{TEXT_PRIMARY};
            border:1px solid #2b3b57;
            border-radius:10px;
            padding: 6px 8px;
        }}
        QLineEdit:focus, QTextEdit:focus, QDateTimeEdit:focus, QComboBox:focus, QSpinBox:focus {{
            border:1px solid #61d6ff;
        }}
        QListWidget {{
            background:#0f1b31;
            border:1px solid #2b3b57;
            border-radius:12px;
            color:{TEXT_PRIMARY};
        }}
        QListWidget::item {{
            border-bottom: 1px solid #22324c;
            padding: 8px 6px;
        }}
        QListWidget::item:selected {{
            background: #233a57;
        }}
        QCalendarWidget QWidget#qt_calendar_navigationbar {{
            background:#16243b;
            border:1px solid #2b3b57;
            border-radius:8px;
        }}
    """


class _DayInsightPopup(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip)
        self.setObjectName("dayInsightPopup")
        self.setStyleSheet(
            f"""
            QFrame#dayInsightPopup {{
                background-color: #0f1c33;
                border: 1px solid #6ee7f9;
                border-radius: 14px;
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: {TEXT_PRIMARY};
            }}
            """
        )
        self.setFixedWidth(420)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(6)

        self.date_lbl = QLabel("YYYY-MM-DD")
        self.date_lbl.setStyleSheet("font-size:22px; font-weight:800; color:#f8f2c8;")
        root.addWidget(self.date_lbl)

        self.top_lbl = QLabel("⌨ Top category: Coding")
        self.top_lbl.setStyleSheet("font-size:15px; color:#f4d879;")
        root.addWidget(self.top_lbl)

        self.prod_lbl = QLabel("✓ Productive: 0m / 0m (0%)")
        self.prod_lbl.setStyleSheet("font-size:15px; color:#66f0bd;")
        root.addWidget(self.prod_lbl)

        self.peak_lbl = QLabel("◷ Peak productive hour: —")
        self.peak_lbl.setStyleSheet("font-size:15px; color:#7cc6ff;")
        root.addWidget(self.peak_lbl)

        graph_title = QLabel("Graph (00→24)")
        graph_title.setStyleSheet("font-size:13px; color:#d7def1;")
        root.addWidget(graph_title)

        self.graph_wrap = QFrame()
        self.graph_wrap.setStyleSheet("background:#111c32; border:1px solid #223552; border-radius:8px;")
        graph_v = QVBoxLayout(self.graph_wrap)
        graph_v.setContentsMargins(8, 8, 8, 4)
        graph_v.setSpacing(4)

        bars_row = QHBoxLayout()
        bars_row.setSpacing(2)
        self._bar_widgets = []
        for _ in range(24):
            bar = QFrame()
            bar.setFixedSize(10, 24)
            bar.setStyleSheet("background:#26354f; border:none; border-radius:3px;")
            self._bar_widgets.append(bar)
            bars_row.addWidget(bar, alignment=Qt.AlignmentFlag.AlignBottom)
        graph_v.addLayout(bars_row)

        ticks = QHBoxLayout()
        ticks.setSpacing(0)
        for t in ["00", "06", "12", "18", "24"]:
            lbl = QLabel(t)
            lbl.setStyleSheet("color:#8e9ab1; font-size:10px;")
            ticks.addWidget(lbl)
            if t != "24":
                ticks.addStretch()
        graph_v.addLayout(ticks)
        root.addWidget(self.graph_wrap)

    def update_data(self, day_key: str, info: dict):
        top = str(info.get("top_category", "unknown")).title()
        total_mins = int(float(info.get("total_secs", 0.0)) // 60)
        prod_mins = int(float(info.get("productive_secs", 0.0)) // 60)
        pct = int(info.get("productivity_pct", 0))
        peak_hour = info.get("peak_hour")
        peak_label = "—" if peak_hour is None else datetime.time(hour=int(peak_hour)).strftime("%I:%M %p").lstrip("0")

        self.date_lbl.setText(day_key)
        self.top_lbl.setText(f"⌨ Top category: {top}")
        self.prod_lbl.setText(f"✓ Productive: {prod_mins}m / {total_mins}m ({pct}%)")
        self.peak_lbl.setText(f"◷ Peak productive hour: {peak_label}")

        hourly = info.get("productive_by_hour", [])
        if not hourly or len(hourly) < 24:
            hourly = [0.0] * 24
        mx = max(hourly) if max(hourly) > 0 else 1.0
        peak_idx = int(max(range(24), key=lambda i: hourly[i])) if any(hourly) else -1
        for i, bar in enumerate(self._bar_widgets):
            ratio = float(hourly[i]) / mx
            h = max(4, int(24 * ratio)) if ratio > 0 else 4
            bar.setFixedHeight(h)
            if i == peak_idx and ratio > 0:
                bar.setStyleSheet("background:#5be7b3; border:none; border-radius:3px;")
            elif ratio > 0.6:
                bar.setStyleSheet("background:#4fa8ff; border:none; border-radius:3px;")
            elif ratio > 0.2:
                bar.setStyleSheet("background:#3a6fb3; border:none; border-radius:3px;")
            else:
                bar.setStyleSheet("background:#26354f; border:none; border-radius:3px;")


class PlannerPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color:{BG_MAIN};")
        self._engine = None
        self._all_tasks = []
        self._history_range_box = None
        self._calendar_markers = {}
        self._calendar_view = None
        self._hover_popup = _DayInsightPopup()
        self._current_hover_day = None
        self._month_marker_cache = {}
        self._prod_ring = None
        self._prod_time_text = None
        self._build()
        self.setStyleSheet(self.styleSheet() + _glass_styles())

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 28)
        root.setSpacing(16)

        title = QLabel("Planner & Tasks")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setStyleSheet("color:#f0d9a1; font-weight:800;")
        root.addWidget(title)

        subtitle = QLabel(
            "Plan tasks on specific dates, track deadlines, and get reminders before time runs out."
        )
        subtitle.setStyleSheet(f"color:{TEXT_SECONDARY}; font-size:12px;")
        root.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, stretch=1)

        # Left: Calendar + quick stats
        left_card = _card()
        left = QVBoxLayout(left_card)
        left.setContentsMargins(16, 14, 16, 14)
        left.setSpacing(10)
        left.addWidget(self._heading("Calendar"))

        self.calendar = PlannerCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.selectionChanged.connect(self.refresh_tasks)
        self.calendar.currentPageChanged.connect(self._refresh_calendar_markers)
        self._calendar_view = self.calendar.findChild(QTableView)
        if self._calendar_view and self._calendar_view.viewport():
            self._calendar_view.viewport().setMouseTracking(True)
            self._calendar_view.viewport().installEventFilter(self)
        self.calendar.setStyleSheet(
            f"""
            QCalendarWidget QWidget {{
                alternate-background-color: {BG_CARD_ALT};
            }}
            QCalendarWidget QToolButton {{
                color:{TEXT_PRIMARY};
                background: transparent;
                border:none;
                font-weight:700;
            }}
            QCalendarWidget QMenu {{
                background:#0f1b31;
                color:{TEXT_PRIMARY};
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                color: {TEXT_PRIMARY};
                selection-background-color: {ACCENT};
                selection-color: white;
                background: #0f1b31;
                outline: 0;
                border: 1px solid #2b3b57;
                border-radius: 10px;
                gridline-color: #24344f;
            }}
            """
        )
        left.addWidget(self.calendar)

        legend_row = QHBoxLayout()
        legend_row.setSpacing(10)
        legend_row.addWidget(self._dot_label("#22c55e", "Productive day"))
        legend_row.addWidget(self._dot_label("#ef4444", "Entertainment-heavy"))
        legend_row.addWidget(self._dot_label("#60a5fa", "Mixed day"))
        legend_row.addStretch()
        left.addLayout(legend_row)

        self._stats_lbl = QLabel("Pending: 0   |   Completed: 0   |   Due today: 0")
        self._stats_lbl.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px;")
        left.addWidget(self._stats_lbl)
        self._task_count_lbl = QLabel("Task count: 0")
        self._task_count_lbl.setStyleSheet("color:#c7d2fe; font-size:10px;")
        left.addWidget(self._task_count_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        body.addWidget(left_card, stretch=1)

        # Right: Add task + list
        right_col = QVBoxLayout()
        right_col.setSpacing(16)
        body.addLayout(right_col, stretch=2)

        form_card = _card()
        form = QVBoxLayout(form_card)
        form.setContentsMargins(16, 14, 16, 14)
        form.setSpacing(10)
        form.addWidget(self._heading("Create Task"))

        self.task_title = QLineEdit()
        self.task_title.setPlaceholderText("Task title (e.g., Prepare report)")
        self.task_desc = QTextEdit()
        self.task_desc.setPlaceholderText("Description / notes (optional)")
        self.task_desc.setFixedHeight(70)

        row = QHBoxLayout()
        self.task_due = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.task_due.setCalendarPopup(True)
        self.task_due.setDisplayFormat("dd MMM yyyy, hh:mm AP")
        self.task_priority = QComboBox()
        self.task_priority.addItems(["high", "medium", "low"])
        self.task_reminder = QSpinBox()
        self.task_reminder.setRange(1, 1440)
        self.task_reminder.setValue(30)
        self.task_reminder.setSuffix(" min early")
        row.addWidget(self.task_due)
        row.addWidget(self.task_priority)
        self._mode_chip = QLabel("⟲")
        self._mode_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._mode_chip.setFixedSize(26, 26)
        self._mode_chip.setStyleSheet(
            "background:#20d6af; color:white; border:1px solid #39f2ca; border-radius:13px; font-weight:700;"
        )
        self._list_chip = QLabel("☰")
        self._list_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._list_chip.setFixedSize(26, 26)
        self._list_chip.setStyleSheet(
            "background:#111d34; color:#7bd8ff; border:1px solid #2f4262; border-radius:13px; font-weight:700;"
        )
        row.addWidget(self._mode_chip)
        row.addWidget(self._list_chip)
        row.addWidget(self.task_reminder)

        self.add_btn = QPushButton("Add Task")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self._add_task)
        self.add_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: #22d3aa;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 8px 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: #2ee6bc; }}
            """
        )

        form.addWidget(self.task_title)
        form.addWidget(self.task_desc)
        form.addLayout(row)
        form.addWidget(self.add_btn, alignment=Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(form_card)

        list_card = _card()
        list_v = QVBoxLayout(list_card)
        list_v.setContentsMargins(16, 14, 16, 14)
        list_v.setSpacing(10)
        list_v.addWidget(self._heading("Tasks"))

        control_row = QHBoxLayout()
        self.filter_box = QComboBox()
        self.filter_box.addItems(["Selected day", "Next 7 days", "All pending", "Completed"])
        self.filter_box.currentIndexChanged.connect(self.refresh_tasks)
        control_row.addWidget(self.filter_box)

        self.complete_btn = QPushButton("Mark Done")
        self.reopen_btn = QPushButton("Reopen")
        self.delete_btn = QPushButton("Delete")
        for b in [self.complete_btn, self.reopen_btn, self.delete_btn]:
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                f"QPushButton{{background:#111d34; color:{TEXT_SECONDARY}; border:1px solid #2b3b57; border-radius:8px; padding:6px 10px;}}"
                f"QPushButton:hover{{color:{TEXT_PRIMARY}; border:1px solid #61d6ff;}}"
            )
        self.complete_btn.clicked.connect(lambda: self._change_selected_status("done"))
        self.reopen_btn.clicked.connect(lambda: self._change_selected_status("pending"))
        self.delete_btn.clicked.connect(self._delete_selected)
        control_row.addWidget(self.complete_btn)
        control_row.addWidget(self.reopen_btn)
        control_row.addWidget(self.delete_btn)
        control_row.addStretch()
        list_v.addLayout(control_row)

        self.task_list = QListWidget()
        list_v.addWidget(self.task_list)
        right_col.addWidget(list_card, stretch=1)

        # Activity Explorer (separate section)
        history_card = _card()
        history_v = QVBoxLayout(history_card)
        history_v.setContentsMargins(16, 14, 16, 14)
        history_v.setSpacing(10)
        history_v.addWidget(self._heading("Activity Explorer"))

        hr = QHBoxLayout()
        hr.addWidget(QLabel("Range:"))
        self._history_range_box = QComboBox()
        self._history_range_box.addItems([
            "Selected day",
            "Week of selected day",
            "Month of selected day",
            "Year of selected day",
        ])
        self._history_range_box.currentIndexChanged.connect(self.refresh_tasks)
        hr.addWidget(self._history_range_box)
        hr.addStretch()
        history_v.addLayout(hr)

        self._activity_summary_lbl = QLabel("Select a date to view insights.")
        self._activity_summary_lbl.setWordWrap(True)
        self._activity_summary_lbl.setStyleSheet("color:#a8b8d8; font-size:12px;")
        history_v.addWidget(self._activity_summary_lbl)

        stats_cards = QHBoxLayout()
        stats_cards.setSpacing(10)
        self._top_cat_card = self._mini_stat_card("Top Category", "—")
        self._top_app_card = self._mini_stat_card("Top App/Site", "—")
        self._prod_card = self._mini_stat_card("Productive time", "—", with_ring=True)
        self._top_cat_card.setMinimumHeight(88)
        self._top_app_card.setMinimumHeight(88)
        self._prod_card.setMinimumHeight(88)
        self._top_cat_card.setMinimumWidth(240)
        self._top_app_card.setMinimumWidth(170)
        self._prod_card.setMinimumWidth(160)
        stats_cards.addWidget(self._top_cat_card, 5)
        stats_cards.addWidget(self._top_app_card, 2)
        stats_cards.addWidget(self._prod_card, 2)
        history_v.addLayout(stats_cards)

        self._activity_list = QListWidget()
        self._activity_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._activity_list.setMinimumHeight(200)
        self._activity_list.setSpacing(6)
        history_v.addWidget(self._activity_list)
        right_col.addWidget(history_card, stretch=1)

    def _heading(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet(f"color:{TEXT_PRIMARY}; font-size:15px; font-weight:800;")
        return l

    def _dot_label(self, color: str, text: str) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(5)
        dot = QLabel("●")
        dot.setStyleSheet(f"color:{color}; font-size:11px;")
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px;")
        h.addWidget(dot)
        h.addWidget(lbl)
        return w

    def _mini_stat_card(self, title: str, value: str, with_ring: bool = False) -> QFrame:
        card = QFrame()
        card.setObjectName("miniStatCard")
        card.setStyleSheet(
            f"""
            QFrame#miniStatCard {{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #111d34, stop:1 #0f1930);
                border:1px solid #2f4262;
                border-radius:10px;
            }}
            QLabel {{
                border:none;
                background:transparent;
            }}
            """
        )
        v = QVBoxLayout(card)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(3)
        t = QLabel(title)
        t.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px; border:none; background:transparent;")
        val = QLabel(value)
        val.setStyleSheet("color:#e6f0ff; font-size:15px; font-weight:800; border:none; background:transparent;")
        val.setWordWrap(True)
        v.addWidget(t)
        if with_ring:
            row = QHBoxLayout()
            row.setSpacing(8)
            row.addWidget(val, 1)
            ring = _RatioRing()
            row.addWidget(ring, 0, Qt.AlignmentFlag.AlignRight)
            v.addLayout(row)
            card._ring = ring
            self._prod_ring = ring
            self._prod_time_text = val
        else:
            v.addWidget(val)
        if title == "Top Category":
            bars = QHBoxLayout()
            bars.setSpacing(3)
            for i, h in enumerate([8, 12, 16, 26, 14]):
                b = QFrame()
                b.setFixedSize(8, h)
                if i == 3:
                    b.setStyleSheet("background:#33d8b1; border:none; border-radius:3px;")
                else:
                    b.setStyleSheet("background:#3b516f; border:none; border-radius:3px;")
                bars.addWidget(b, alignment=Qt.AlignmentFlag.AlignBottom)
            bars.addStretch()
            v.addLayout(bars)
        card._val_label = val
        return card

    def set_engine(self, engine):
        self._engine = engine
        self._refresh_calendar_markers()
        self.refresh_tasks()

    def _add_task(self):
        if not self._engine:
            return
        title = self.task_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Planner", "Please enter a task title.")
            return
        due_dt = self.task_due.dateTime().toPyDateTime()
        self._engine.db_manager.add_task(
            title=title,
            description=self.task_desc.toPlainText(),
            due_ts=due_dt.timestamp(),
            priority=self.task_priority.currentText(),
            remind_before_min=self.task_reminder.value(),
        )
        self.task_title.clear()
        self.task_desc.clear()
        self.refresh_tasks()

    def refresh_tasks(self):
        if not self._engine:
            return
        mode = self.filter_box.currentText() if hasattr(self, "filter_box") else "Selected day"
        all_tasks = self._engine.db_manager.get_tasks()
        self._all_tasks = all_tasks

        now = datetime.datetime.now().timestamp()
        sel_date = self.calendar.selectedDate().toPyDate()
        selected_day_tasks = self._engine.db_manager.get_tasks_due_on_date(sel_date)

        if mode == "Selected day":
            tasks = selected_day_tasks
        elif mode == "Next 7 days":
            end = now + 7 * 24 * 3600
            tasks = [t for t in all_tasks if now <= t["due_ts"] <= end and t["status"] == "pending"]
        elif mode == "Completed":
            tasks = [t for t in all_tasks if t["status"] == "done"]
        else:
            tasks = [t for t in all_tasks if t["status"] == "pending"]

        self.task_list.clear()
        for t in tasks:
            due_dt = datetime.datetime.fromtimestamp(t["due_ts"])
            due_txt = due_dt.strftime("%d %b %Y, %I:%M %p")
            status = "DONE" if t["status"] == "done" else "PENDING"
            overdue = (t["status"] == "pending" and t["due_ts"] < now)
            badge = "OVERDUE" if overdue else status
            pri = str(t.get("priority", "medium")).upper()
            desc = t["description"].strip()
            icon = "✅" if t["status"] == "done" else ("⚠" if overdue else "🗂")
            line1 = f"{icon} [{badge}]  {t['title']}  •  {pri}"
            line2 = f"Due: {due_txt}   •   Remind: {t.get('remind_before_min', 30)} min early"
            text = line1 + "\n" + line2 + (f"\n{desc}" if desc else "")
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, t["id"])
            if overdue:
                item.setForeground(Qt.GlobalColor.red)
            self.task_list.addItem(item)

        if not tasks:
            self.task_list.clear()
            empty_item = QListWidgetItem("📄  No tasks yet for this day. Ready to add one?")
            empty_item.setForeground(QColor("#93a4c4"))
            self.task_list.addItem(empty_item)

        pending = len([t for t in all_tasks if t["status"] == "pending"])
        done = len([t for t in all_tasks if t["status"] == "done"])
        due_today = len([t for t in selected_day_tasks if t["status"] == "pending"])
        self._stats_lbl.setText(f"Pending: {pending}   |   Completed: {done}   |   Due on selected day: {due_today}")
        self._task_count_lbl.setText(f"Task count: {len(all_tasks)}")
        self._refresh_calendar_markers()
        self._refresh_activity_insights()

    def _selected_time_range(self) -> tuple[float, float]:
        sel_date = self.calendar.selectedDate().toPyDate()
        mode = self._history_range_box.currentText() if self._history_range_box else "Selected day"

        if mode == "Week of selected day":
            start_date = sel_date - datetime.timedelta(days=sel_date.weekday())
            end_date = start_date + datetime.timedelta(days=6)
        elif mode == "Month of selected day":
            start_date = sel_date.replace(day=1)
            if start_date.month == 12:
                next_month = datetime.date(start_date.year + 1, 1, 1)
            else:
                next_month = datetime.date(start_date.year, start_date.month + 1, 1)
            end_date = next_month - datetime.timedelta(days=1)
        elif mode == "Year of selected day":
            start_date = datetime.date(sel_date.year, 1, 1)
            end_date = datetime.date(sel_date.year, 12, 31)
        else:
            start_date = sel_date
            end_date = sel_date

        start_ts = datetime.datetime.combine(start_date, datetime.time.min).timestamp()
        end_ts = datetime.datetime.combine(end_date, datetime.time.max).timestamp()
        return start_ts, end_ts

    def _refresh_activity_insights(self):
        if not self._engine:
            return
        start_ts, end_ts = self._selected_time_range()
        db = self._engine.db_manager
        summary = db.get_activity_summary(start_ts, end_ts)
        sessions = db.get_activity_sessions(start_ts, end_ts, limit=800)

        total_min = int(summary["total_secs"] // 60)
        prod_min = int(summary["productive_secs"] // 60)
        ratio = int((prod_min / total_min) * 100) if total_min > 0 else 0
        top_cat = str(summary["top_category"]).title()
        top_app = summary["top_app"]
        self._activity_summary_lbl.setText(
            f"Top category: {top_cat}  |  Top app/site: {top_app}\n"
            f"Productive time: {prod_min}m / {total_min}m ({ratio}%)"
        )
        self._top_cat_card._val_label.setText(top_cat)
        self._top_app_card._val_label.setText(str(top_app))
        if self._prod_time_text:
            self._prod_time_text.setText(f"{prod_min}m / {total_min}m ({ratio}%)")
        if self._prod_ring:
            self._prod_ring.set_value(max(0, min(100, ratio)))
        self._prod_card._val_label.setText(f"{ratio}%")

        self._activity_list.clear()
        if not sessions:
            empty = QListWidgetItem("🧭  No activity data in this range yet. Start tracking apps to see timeline insights.")
            empty.setForeground(QColor("#93a4c4"))
            self._activity_list.addItem(empty)
            return

        for s in sessions:
            st = datetime.datetime.fromtimestamp(s["start_time"]).strftime("%d %b %H:%M")
            et = datetime.datetime.fromtimestamp(s["end_time"]).strftime("%H:%M")
            task_title = s["title"] if s["title"] and s["title"] != "Unknown Title" else s["app"]
            if len(task_title) > 58:
                task_title = task_title[:55] + "..."
            domain = f" • {s['domain']}" if s.get("domain") else ""
            mins = max(1, int(float(s["duration"]) // 60))
            cat = str(s["category"]).title()
            cat_icon = "💻" if cat == "Coding" else ("🎬" if cat == "Entertainment" else ("📚" if cat == "Learning" else "•"))
            item = QListWidgetItem()
            row_widget = self._make_activity_row(
                icon=cat_icon,
                meta=f"{st}   [{cat}]   {mins}m",
                title=task_title,
                source=f"{s['app']}{domain}",
                app_chip=(s.get("domain") or s.get("app") or "App"),
                category=cat,
            )
            item.setSizeHint(row_widget.sizeHint())
            self._activity_list.addItem(item)
            self._activity_list.setItemWidget(item, row_widget)

    def _make_activity_row(
        self,
        icon: str,
        meta: str,
        title: str,
        source: str,
        app_chip: str,
        category: str,
    ) -> QWidget:
        wrap = QFrame()
        wrap.setObjectName("activityRow")
        wrap.setStyleSheet(
            """
            QFrame#activityRow {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 rgba(19,31,55,0.88), stop:1 rgba(17,28,48,0.78));
                border: 1px solid #3a4f71;
                border-radius: 10px;
            }
            """
        )
        h = QHBoxLayout(wrap)
        h.setContentsMargins(8, 5, 8, 5)
        h.setSpacing(10)

        badge = QLabel(icon)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(24, 24)
        if category in {"Coding", "Learning", "Writing"}:
            badge.setStyleSheet("background:#12364a; border:1px solid #2fd6b4; border-radius:6px;")
        elif category in {"Entertainment", "Browsing"}:
            badge.setStyleSheet("background:#3a1e32; border:1px solid #ff6b6b; border-radius:6px;")
        else:
            badge.setStyleSheet("background:#1f2f4a; border:1px solid #4f79b8; border-radius:6px;")
        h.addWidget(badge)

        v = QVBoxLayout()
        v.setSpacing(0)
        meta_lbl = QLabel(meta)
        meta_lbl.setStyleSheet("color:#a8b8d8; font-size:10px; border:none; background:transparent;")
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color:#e7efff; font-size:11px; font-weight:700; border:none; background:transparent;")
        source_text = source.replace(" • ", " ")
        source_lbl = QLabel(source_text)
        source_lbl.setStyleSheet("color:#66d7bf; font-size:10px; border:none; background:transparent;")
        source_lbl.setMaximumHeight(14)
        v.addWidget(meta_lbl)
        v.addWidget(title_lbl)
        v.addWidget(source_lbl)
        h.addLayout(v, 1)

        chip_text = str(app_chip).split(" ")[0]
        if "youtube" in chip_text.lower():
            chip_text = "🔴 YouTube"
        elif "chrome" in chip_text.lower():
            chip_text = "🌐 Chrome"
        elif "python" in chip_text.lower():
            chip_text = "🐍 Python"
        elif "code" in chip_text.lower() or "cursor" in chip_text.lower():
            chip_text = "⌨ Code"
        chip = QLabel(chip_text)
        chip.setStyleSheet(
            "background:#1a2a43; color:#e6f0ff; border:1px solid #3f5777; border-radius:8px; padding:3px 9px; font-size:10px;"
        )
        h.addWidget(chip, 0, Qt.AlignmentFlag.AlignVCenter)
        return wrap

    def _refresh_calendar_markers(self):
        if not self._engine:
            return

        year = self.calendar.yearShown()
        month = self.calendar.monthShown()
        self._calendar_markers = self._engine.db_manager.get_monthly_day_activity_tags(year, month)
        self._month_marker_cache[(year, month)] = self._calendar_markers
        if isinstance(self.calendar, PlannerCalendarWidget):
            self.calendar.set_day_markers(self._calendar_markers)

        # Clear date formats for the visible month first
        first = datetime.date(year, month, 1)
        if month == 12:
            next_month = datetime.date(year + 1, 1, 1)
        else:
            next_month = datetime.date(year, month + 1, 1)

        day = first
        while day < next_month:
            self.calendar.setDateTextFormat(
                QDate(day.year, day.month, day.day),
                QTextCharFormat(),
            )
            day += datetime.timedelta(days=1)

        # Apply markers
        for day_key, info in self._calendar_markers.items():
            d = datetime.date.fromisoformat(day_key)
            if d.year != year or d.month != month:
                continue

            fmt = QTextCharFormat()
            tag = info.get("tag", "mixed")
            top = str(info.get("top_category", "unknown")).title()
            mins = int(float(info.get("total_secs", 0.0)) // 60)

            if tag == "productive":
                fmt.setForeground(QColor("#22c55e"))
            elif tag == "entertainment":
                fmt.setForeground(QColor("#ef4444"))
            else:
                fmt.setForeground(QColor("#60a5fa"))

            fmt.setFontWeight(QFont.Weight.Bold)
            self.calendar.setDateTextFormat(QDate(d.year, d.month, d.day), fmt)

    def eventFilter(self, obj, event):
        """
        Reliable hover tooltip for calendar date cells.
        """
        if (
            self._calendar_view
            and obj is self._calendar_view.viewport()
            and event.type() == QEvent.Type.MouseMove
        ):
            index = self._calendar_view.indexAt(event.pos())
            if index.isValid():
                qdate = self._date_from_index(index)
                if isinstance(qdate, QDate) and qdate.isValid():
                    day_key = qdate.toPyDate().isoformat()
                    info = self._get_day_info(qdate.toPyDate())
                    if self._current_hover_day != day_key:
                        self._hover_popup.update_data(day_key, info)
                        self._current_hover_day = day_key
                    self._hover_popup.move(event.globalPosition().toPoint() + QPoint(14, 14))
                    self._hover_popup.show()
                else:
                    self._hover_popup.hide()
                    self._current_hover_day = None
            else:
                self._hover_popup.hide()
                self._current_hover_day = None
        elif (
            self._calendar_view
            and obj is self._calendar_view.viewport()
            and event.type() == QEvent.Type.Leave
        ):
            self._hover_popup.hide()
            self._current_hover_day = None
        return super().eventFilter(obj, event)

    def _date_from_index(self, index) -> QDate | None:
        """
        Convert a hovered calendar index to actual date.
        Uses displayed day number and row position to infer prev/current/next month.
        """
        if not index.isValid():
            return None
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "").strip()
        if not text.isdigit():
            return None
        day_num = int(text)

        year = self.calendar.yearShown()
        month = self.calendar.monthShown()
        row = index.row()

        # Heuristic:
        # - first two rows with large day numbers -> previous month
        # - last two rows with small day numbers -> next month
        if row <= 1 and day_num > 20:
            if month == 1:
                return QDate(year - 1, 12, day_num)
            return QDate(year, month - 1, day_num)
        if row >= 4 and day_num < 15:
            if month == 12:
                return QDate(year + 1, 1, day_num)
            return QDate(year, month + 1, day_num)
        return QDate(year, month, day_num)

    def _get_day_info(self, day: datetime.date) -> dict:
        """
        Fetch day marker info from cache/db. Returns a safe default if no activity exists.
        """
        ym = (day.year, day.month)
        if ym not in self._month_marker_cache:
            self._month_marker_cache[ym] = self._engine.db_manager.get_monthly_day_activity_tags(day.year, day.month)
        info = self._month_marker_cache[ym].get(day.isoformat())
        if info:
            return info
        return {
            "top_category": "none",
            "total_secs": 0.0,
            "productive_secs": 0.0,
            "tag": "mixed",
            "productivity_pct": 0,
            "peak_hour": None,
            "productive_by_hour": [0.0] * 24,
        }

    def _selected_task_id(self):
        item = self.task_list.currentItem()
        if not item:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _change_selected_status(self, status: str):
        if not self._engine:
            return
        task_id = self._selected_task_id()
        if task_id is None:
            QMessageBox.information(self, "Planner", "Select a task first.")
            return
        self._engine.db_manager.update_task_status(task_id, status)
        self.refresh_tasks()

    def _delete_selected(self):
        if not self._engine:
            return
        task_id = self._selected_task_id()
        if task_id is None:
            QMessageBox.information(self, "Planner", "Select a task first.")
            return
        self._engine.db_manager.delete_task(task_id)
        self.refresh_tasks()
