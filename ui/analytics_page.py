from __future__ import annotations
import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QSizePolicy,
    QSpacerItem,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QBrush

from widgets.charts import TimelineBarChart, DonutChart, CategoryBar
from ui.ui_effects import apply_soft_shadow

from styles.theme import (
    BG_MAIN, BG_CARD, BG_CARD_ALT, BORDER,
    ACCENT, ACCENT_PURPLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    GREEN, YELLOW,
)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _lbl(text: str, size: int = 12, bold: bool = False,
         color: str = TEXT_PRIMARY, wrap: bool = False) -> QLabel:
    w = QFont.Weight.Bold if bold else QFont.Weight.Normal
    l = QLabel(text)
    l.setFont(QFont("Segoe UI", size, w))
    l.setStyleSheet(f"color:{color}; background:transparent; border:none;")
    if wrap:
        l.setWordWrap(True)
    return l


def _divider(vertical: bool = False) -> QFrame:
    f = QFrame()
    if vertical:
        f.setFrameShape(QFrame.Shape.VLine)
        f.setFixedWidth(1)
    else:
        f.setFrameShape(QFrame.Shape.HLine)
        f.setFixedHeight(1)
    f.setStyleSheet(f"background:{BORDER}; border:none;")
    return f


def _card(radius: int = 14) -> QFrame:
    f = QFrame()
    f.setStyleSheet(f"""
        QFrame {{
            background-color: {BG_CARD};
            border: 1px solid {BORDER};
            border-radius: {radius}px;
        }}
    """)
    return f


# ─────────────────────────────────────────────────────────────────────────────
#  Activity Timeline Card
# ─────────────────────────────────────────────────────────────────────────────

class ActivityTimelineCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 14px;
            }}
        """)
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 18, 22, 18)
        v.setSpacing(0)

        # header row
        h = QHBoxLayout()
        h.addWidget(_lbl("Activity Timeline", 14, bold=True))
        h.addStretch()

        # legend
        for dot_color, legend_text in [
            (ACCENT_PURPLE, "Focus"),
            ("#6e7681",     "Idle"),
        ]:
            dot = QLabel("●")
            dot.setStyleSheet(
                f"color:{dot_color}; font-size:9px; background:transparent;")
            h.addWidget(dot)
            h.addSpacing(3)
            h.addWidget(_lbl(legend_text, 10, color=TEXT_SECONDARY))
            h.addSpacing(12)

        v.addLayout(h)
        v.addSpacing(14)

        # chart
        self.chart = TimelineBarChart(sessions=[])
        self.chart.setFixedHeight(120)
        v.addWidget(self.chart)

    def update_data(self, sessions_data: list, time_frame: str = "day"):
        self.chart.time_frame = time_frame
        self.chart.sessions = sessions_data
        self.chart.update()


# ─────────────────────────────────────────────────────────────────────────────
#  Peak Productivity Heatmap Card
# ─────────────────────────────────────────────────────────────────────────────

class _HeatmapBlock(QFrame):
    def __init__(self, color: str, tooltip: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
        self.setToolTip(tooltip)


class PeakProductivityCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 14px;
            }}
        """)
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 18, 22, 18)
        v.setSpacing(10)

        v.addWidget(_lbl("Peak Productivity Hours", 14, bold=True))
        self._peak_summary = _lbl(
            "No strong focus hour yet. Keep tracking to reveal your peak time.",
            10,
            color=TEXT_SECONDARY,
            wrap=True,
        )
        v.addWidget(self._peak_summary)

        self.grid = QHBoxLayout()
        self.grid.setSpacing(5)
        
        # Initialize 24 blocks for the hours 0-23
        self.blocks = []
        for h in range(24):
            time_str = f"{h:02d}:00"
            block = _HeatmapBlock("#2d3748", f"{time_str} - No data")
            self.grid.addWidget(block)
            self.blocks.append(block)

        v.addLayout(self.grid)

        marker_row = QHBoxLayout()
        marker_row.setContentsMargins(0, 0, 0, 0)
        marker_row.addWidget(_lbl("12a", 9, color=TEXT_MUTED))
        marker_row.addStretch()
        marker_row.addWidget(_lbl("6a", 9, color=TEXT_MUTED))
        marker_row.addStretch()
        marker_row.addWidget(_lbl("12p", 9, color=TEXT_MUTED))
        marker_row.addStretch()
        marker_row.addWidget(_lbl("6p", 9, color=TEXT_MUTED))
        marker_row.addStretch()
        marker_row.addWidget(_lbl("11p", 9, color=TEXT_MUTED))
        v.addLayout(marker_row)

        legend = QHBoxLayout()
        legend.setSpacing(8)
        legend.addWidget(_lbl("Low", 9, color=TEXT_MUTED))
        for color in ("#2d3748", "#1d4ed8", "#3b82f6", "#60a5fa"):
            chip = QFrame()
            chip.setFixedSize(14, 10)
            chip.setStyleSheet(f"background:{color}; border:none; border-radius:3px;")
            legend.addWidget(chip)
        legend.addWidget(_lbl("High", 9, color=TEXT_MUTED))
        legend.addStretch()
        v.addLayout(legend)

    def update_data(self, timeline_data: list, time_frame: str = "day"):
        # We calculate the focus duration per hour
        hour_durations = [0] * 24
        for s in timeline_data:
            cat = s.get("category", "").lower()
            if cat in ["coding", "learning", "writing", "communication"]:
                st_hour = int(s["start"])
                # Extract duration in minutes from duration string "Xh Ym" or "Xm"
                duration_str = s.get("duration", "0m")
                mins = 0
                if "h" in duration_str and "m" in duration_str:
                    parts = duration_str.split("h")
                    try:
                        mins = int(parts[0].strip()) * 60 + int(parts[1].replace("m", "").strip())
                    except ValueError:
                        pass
                elif "m" in duration_str:
                    try:
                        mins = int(duration_str.replace("m", "").strip())
                    except ValueError:
                        pass
                
                # Assign this duration mostly to the start hour (simple approximation)
                if 0 <= st_hour < 24:
                    hour_durations[st_hour] += mins

        # Update blocks
        max_dur = max(hour_durations) if max(hour_durations) > 0 else 1
        peak_hour = max(range(24), key=lambda i: hour_durations[i]) if any(hour_durations) else None
        peak_minutes = hour_durations[peak_hour] if peak_hour is not None else 0

        frame_label = {
            "day": "today",
            "week": "this week",
            "month": "this month",
            "year": "this year",
        }.get(time_frame, "the selected period")

        if peak_hour is None or peak_minutes <= 0:
            self._peak_summary.setText(
                f"No strong focus hour in {frame_label} yet. Keep tracking to reveal your peak time."
            )
        else:
            hour_label = datetime.time(hour=peak_hour).strftime("%I:%M %p").lstrip("0")
            self._peak_summary.setText(
                f"Best focus window in {frame_label}: {hour_label} ({peak_minutes} min productive time)."
            )

        for h in range(24):
            dur = hour_durations[h]
            if dur == 0:
                color = "#2d3748"
            else:
                ratio = dur / max_dur
                if ratio < 0.3:
                    color = "#1d4ed8"  # Dark blue
                elif ratio < 0.7:
                    color = "#3b82f6"  # Blue
                else:
                    color = "#60a5fa"  # Light/bright blue
                    
            hour_str = f"{h:02d}:00"
            time_val = f"{dur // 60}h {dur % 60}m" if dur >= 60 else f"{dur}m"
            self.blocks[h].setStyleSheet(f"background-color: {color}; border-radius: 4px;")
            self.blocks[h].setToolTip(f"{hour_str} - Deep Work: {time_val}")


# ─────────────────────────────────────────────────────────────────────────────
#  Total Active Time Card  (donut + legend)
# ─────────────────────────────────────────────────────────────────────────────

class TotalActiveTimeCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 14px;
            }}
        """)
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 18, 20, 20)
        v.setSpacing(0)

        v.addWidget(_lbl("Total Active Time", 13, bold=True))
        v.addSpacing(18)

        # donut chart centred
        self.donut = DonutChart(
            segments=[],
            center_text="0h 0m",
            center_sub="Total Time",
            size=190,
            thickness=30,
        )
        donut_row = QHBoxLayout()
        donut_row.addStretch()
        donut_row.addWidget(self.donut)
        donut_row.addStretch()
        v.addLayout(donut_row)

        v.addSpacing(18)
        v.addWidget(_divider())
        v.addSpacing(14)

        # legend container
        self.legend_layout = QVBoxLayout()
        self.legend_layout.setSpacing(6)
        v.addLayout(self.legend_layout)
        v.addStretch()

    def update_data(self, breakdown: list, total_seconds: float):
        h = int(total_seconds // 3600)
        m = int((total_seconds % 3600) // 60)
        self.donut.center_text = f"{h}h {m}m"

        color_map = {
            "Coding": "#3b82f6",
            "Learning": "#10b981",
            "Writing": "#f59e0b",
            "Communication": "#8b5cf6",
            "Entertainment": "#ef4444",
            "Designing": "#ec4899",
            "Browsing": "#64748b",
            "Meetings": "#06b6d4",
            "Planning": "#8b5cf6",
            "Reading": "#14b8a6",
            "Unknown": "#6e7681"
        }

        segments = []
        for cat, pct, dur in breakdown:
            segments.append((cat.title(), pct, color_map.get(cat.title(), "#6e7681")))
        
        self.donut.segments = segments
        self.donut.update()

        # clear legend
        def clear_layout(layout):
            if layout is not None:
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget is not None:
                        widget.deleteLater()
                    else:
                        clear_layout(item.layout())
        clear_layout(self.legend_layout)

        for name, pct, color in segments:
            row = QHBoxLayout()
            row.setSpacing(8)
            dot = QLabel("●")
            dot.setStyleSheet(f"color:{color}; font-size:10px; background:transparent;")
            row.addWidget(dot)
            row.addWidget(_lbl(name, 11))
            row.addStretch()
            row.addWidget(_lbl(f"{int(pct)}%", 11, bold=True))
            self.legend_layout.addLayout(row)


# ─────────────────────────────────────────────────────────────────────────────
#  Categories Card
# ─────────────────────────────────────────────────────────────────────────────

class CategoriesCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 14px;
            }}
        """)
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 18, 20, 20)
        v.setSpacing(0)

        # header
        h = QHBoxLayout()
        h.addWidget(_lbl("Categories", 13, bold=True))
        h.addStretch()
        h.addWidget(_lbl("Sort by: Time", 10, color=TEXT_SECONDARY))
        v.addLayout(h)

        v.addSpacing(18)

        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(10)
        v.addLayout(self.rows_layout)
        v.addStretch()

    def update_data(self, breakdown: list):
        # Clear existing
        while self.rows_layout.count():
            child = self.rows_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        color_map = {
            "Coding": "#3b82f6", "Learning": "#10b981", "Writing": "#f59e0b",
            "Communication": "#8b5cf6", "Entertainment": "#ef4444", 
            "Designing": "#ec4899", "Browsing": "#64748b", "Meetings": "#06b6d4",
            "Planning": "#8b5cf6", "Reading": "#14b8a6", "Unknown": "#6e7681"
        }
        
        for name, pct, dur in breakdown:
            name_title = name.title()
            h = int(dur // 3600)
            m = int((dur % 3600) // 60)
            time_str = f"{h}h {m}m" if h > 0 else f"{m}m"
            color = color_map.get(name_title, "#6e7681")

            row_w = QWidget()
            row_w.setStyleSheet("background:transparent;")
            row_v = QVBoxLayout(row_w)
            row_v.setContentsMargins(0, 0, 0, 0)
            row_v.setSpacing(6)

            top = QHBoxLayout()
            top.setSpacing(10)
            pct_lbl = _lbl(f"{int(pct)}%", 10, color=TEXT_MUTED)
            pct_lbl.setFixedWidth(30)
            top.addWidget(pct_lbl)

            top.addWidget(_lbl(name_title, 12))
            top.addStretch()
            top.addWidget(_lbl(time_str, 12, bold=True))

            edit_btn = QPushButton("✎")
            edit_btn.setFixedSize(22, 22)
            edit_btn.setStyleSheet(f"QPushButton {{ background:transparent; color:{TEXT_MUTED}; border:none; font-size:11px; }} QPushButton:hover{{ color:{TEXT_PRIMARY}; }}")
            top.addWidget(edit_btn)
            row_v.addLayout(top)

            bar = CategoryBar(percentage=pct, color=color)
            row_v.addWidget(bar)

            self.rows_layout.addWidget(row_w)


# ─────────────────────────────────────────────────────────────────────────────
#  Apps & Websites Card
# ─────────────────────────────────────────────────────────────────────────────

class _AppRow(QWidget):
    def __init__(
        self,
        pct: str,
        name: str,
        category: str,
        time: str,
        color: str,
        parent=None,
    ):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 6, 0, 6)
        h.setSpacing(12)

        pct_lbl = _lbl(pct, 10, color=TEXT_MUTED)
        pct_lbl.setFixedWidth(28)
        h.addWidget(pct_lbl)

        bar = QFrame()
        bar.setFixedSize(4, 30)
        bar.setStyleSheet(
            f"background:{color}; border-radius:2px; border:none;")
        h.addWidget(bar)

        info = QVBoxLayout()
        info.setSpacing(2)
        info.addWidget(_lbl(name, 12, bold=True))
        info.addWidget(_lbl(category, 10, color=TEXT_MUTED))
        h.addLayout(info)

        h.addStretch()
        h.addWidget(_lbl(time, 12, bold=True))


class AppsWebsitesCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 14px;
            }}
        """)
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 18, 20, 20)
        v.setSpacing(0)

        # header row with filter tabs
        h = QHBoxLayout()
        h.addWidget(_lbl("Apps & Websites", 13, bold=True))
        h.addStretch()

        for tab, active in [("All", True), ("Apps", False)]:
            btn = QPushButton(tab)
            btn.setFixedSize(50, 26)
            btn.setFont(QFont("Segoe UI", 10))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {BG_CARD_ALT};
                        color: {TEXT_PRIMARY};
                        border: 1px solid {BORDER};
                        border-radius: 7px;
                        font-weight: 600;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {TEXT_SECONDARY};
                        border: none;
                        border-radius: 7px;
                    }}
                    QPushButton:hover {{ color: {TEXT_PRIMARY}; }}
                """)
            h.addWidget(btn)
            h.addSpacing(2)

        v.addLayout(h)
        v.addSpacing(14)
        v.addWidget(_divider())

        self.rows_layout = QVBoxLayout()
        v.addLayout(self.rows_layout)
        v.addStretch()
        
    def update_data(self, usage: list):
        while self.rows_layout.count():
            child = self.rows_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        # usage = [(app_name, pct, dur)]
        colors = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444", "#6e7681"]
        for i, (name, pct, dur) in enumerate(usage[:8]): # Top 8
            h = int(dur // 3600)
            m = int((dur % 3600) // 60)
            time_str = f"{h}h {m}m" if h > 0 else f"{m}m"
            color = colors[i % len(colors)]
            
            self.rows_layout.addWidget(_AppRow(f"{int(pct)}%", name, "App", time_str, color))
            self.rows_layout.addWidget(_divider())


# ─────────────────────────────────────────────────────────────────────────────
#  Analytics Page  (root widget)
# ─────────────────────────────────────────────────────────────────────────────

class AnalyticsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color:{BG_MAIN};")
        self.time_frame = "day"
        self._engine = None
        self._tab_buttons = []
        self._build()

    def _build(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background:transparent; border:none; }")

        container = QWidget()
        container.setStyleSheet(f"background-color:{BG_MAIN};")
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        root = QVBoxLayout(container)
        root.setContentsMargins(28, 24, 28, 28)
        root.setSpacing(0)

        # ── Page header ───────────────────────────────────────────────────────
        root.addLayout(self._build_header())
        root.addSpacing(22)

        # ── Activity timeline ─────────────────────────────────────────────────
        self.timeline_card = ActivityTimelineCard()
        apply_soft_shadow(self.timeline_card)
        root.addWidget(self.timeline_card)
        root.addSpacing(18)

        # ── Peak Productivity ─────────────────────────────────────────────────
        self.peak_card = PeakProductivityCard()
        apply_soft_shadow(self.peak_card)
        root.addWidget(self.peak_card)
        root.addSpacing(18)

        # ── Bottom three panels ───────────────────────────────────────────────
        bottom = QHBoxLayout()
        bottom.setSpacing(16)

        self.total_card = TotalActiveTimeCard()
        self.total_card.setFixedWidth(250)
        apply_soft_shadow(self.total_card, blur_radius=24, offset_y=5, alpha=62)
        bottom.addWidget(self.total_card)

        self.cat_card = CategoriesCard()
        self.cat_card.setMinimumWidth(280)
        apply_soft_shadow(self.cat_card, blur_radius=24, offset_y=5, alpha=62)
        bottom.addWidget(self.cat_card, stretch=1)

        self.apps_card = AppsWebsitesCard()
        self.apps_card.setMinimumWidth(300)
        apply_soft_shadow(self.apps_card, blur_radius=24, offset_y=5, alpha=62)
        bottom.addWidget(self.apps_card, stretch=1)

        root.addLayout(bottom)
        root.addStretch()

    def refresh_data(self, engine):
        if not engine:
            return
            
        self._engine = engine
            
        # Update Timeline
        timeline = engine.get_timeline_data(self.time_frame)
        self.timeline_card.update_data(timeline, self.time_frame)
        
        # Update Peak Productivity
        self.peak_card.update_data(timeline, self.time_frame)
        
        # Update Categories & Total Time
        breakdown = engine.get_category_breakdown(self.time_frame)
        total_secs = engine.get_total_time(self.time_frame)
        self.total_card.update_data(breakdown, total_secs)
        self.cat_card.update_data(breakdown)
        
        # Update Apps List
        usage = engine.get_app_usage(self.time_frame)
        self.apps_card.update_data(usage)

    # ── header builder ────────────────────────────────────────────────────────
    def _build_header(self) -> QVBoxLayout:
        v = QVBoxLayout()
        v.setSpacing(4)

        # Dynamic current date
        import datetime
        today = datetime.datetime.now()
        date_str = today.strftime("📅  %A, %b %d, %Y")
        date_lbl = _lbl(date_str, 11, color=ACCENT)
        date_lbl.setStyleSheet(f"color:{ACCENT}; background:transparent;")
        v.addWidget(date_lbl)


        # title + controls row
        h = QHBoxLayout()
        h.setSpacing(0)

        # ── Sidebar Toggle Button ─────────────────────────────────────────────
        toggle_btn = QPushButton("☰")
        toggle_btn.setFixedSize(36, 36)
        toggle_btn.setFont(QFont("Segoe UI", 16))
        toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {TEXT_PRIMARY};
            }}
            QPushButton:hover {{
                color: {ACCENT};
            }}
        """)
        toggle_btn.clicked.connect(self._toggle_sidebar)
        h.addWidget(toggle_btn)
        h.addSpacing(16)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        title_col.addWidget(_lbl("Daily Activity Analysis", 22, bold=True))
        title_col.addWidget(
            _lbl("Detailed breakdown of your focus sessions and app usage.",
                 12, color=TEXT_SECONDARY))
        h.addLayout(title_col)
        h.addStretch()

        # Day / Week / Month toggle
        tab_frame = QFrame()
        tab_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 10px;
            }}
        """)
        tab_h = QHBoxLayout(tab_frame)
        tab_h.setContentsMargins(4, 4, 4, 4)
        tab_h.setSpacing(2)

        for tab_name, tf in [("Day", "day"), ("Week", "week"), ("Month", "month"), ("Year", "year")]:
            btn = QPushButton(tab_name)
            btn.setFixedSize(60, 28)
            btn.setFont(QFont("Segoe UI", 11))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Use default arg to bind lambda
            btn.clicked.connect(lambda checked, t=tf: self._set_time_frame(t))
            self._tab_buttons.append((tf, btn))
            tab_h.addWidget(btn)
            
        self._update_tab_styles()

        h.addWidget(tab_frame)
        h.addSpacing(12)

        # Share button
        share_btn = QPushButton("  ⇗  Share")
        share_btn.setFixedSize(100, 36)
        share_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        share_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        share_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT};
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #2563eb;
            }}
        """)
        h.addWidget(share_btn)

        v.addLayout(h)
        return v

    def _set_time_frame(self, tf: str):
        self.time_frame = tf
        self._update_tab_styles()
        if self._engine:
            self.refresh_data(self._engine)

    def _update_tab_styles(self):
        for tf, btn in self._tab_buttons:
            if tf == self.time_frame:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {BG_CARD_ALT};
                        color: {TEXT_PRIMARY};
                        border: none;
                        border-radius: 7px;
                        font-weight: 700;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {TEXT_SECONDARY};
                        border: none;
                        border-radius: 7px;
                    }}
                    QPushButton:hover {{ color:{TEXT_PRIMARY}; }}
                """)

    def _toggle_sidebar(self):
        main_win = self.window()
        if hasattr(main_win, '_sidebar'):
            main_win._sidebar.toggle_sidebar()
