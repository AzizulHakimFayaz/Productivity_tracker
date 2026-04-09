from __future__ import annotations

import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QSizePolicy,
    QSpacerItem, QGridLayout, QBoxLayout,
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QLinearGradient

from ui.attention_dialog import show_attention_dialog

from widgets.circular_progress import CircularProgress
from widgets.charts import MiniLineChart
from ui.ui_effects import apply_soft_shadow

from styles.theme import (
    BG_MAIN, BG_CARD, BG_CARD_ALT, BORDER,
    ACCENT, ACCENT_PURPLE, ACTIVE_CARD,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    GREEN, YELLOW, DANGER, ORANGE,
)


# ─── tiny helpers ─────────────────────────────────────────────────────────────

def _lbl(text: str, size: int = 12, bold: bool = False,
         color: str = TEXT_PRIMARY, wrap: bool = False) -> QLabel:
    w = QFont.Weight.Bold if bold else QFont.Weight.Normal
    l = QLabel(text)
    l.setFont(QFont("Segoe UI", size, w))
    l.setStyleSheet(f"color:{color}; background:transparent; border: none;")
    if wrap:
        l.setWordWrap(True)
    return l


def _card(radius: int = 12, bg: str = BG_CARD) -> QFrame:
    f = QFrame()
    f.setStyleSheet(f"""
        QFrame {{
            background-color: {bg};
            border: 1px solid {BORDER};
            border-radius: {radius}px;
        }}
    """)
    return f


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


def _get_greeting() -> str:
    hour = datetime.datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    else:
        return "Good evening"


# ─────────────────────────────────────────────────────────────────────────────
#  Focus Score Card
# ─────────────────────────────────────────────────────────────────────────────

class FocusScoreCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 14px;
            }}
        """)
        self.setMinimumWidth(190)
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 18, 20, 18)
        v.setSpacing(0)

        title = _lbl("FOCUS SCORE", 9, color=TEXT_SECONDARY)
        title.setStyleSheet(
            f"color:{TEXT_SECONDARY}; letter-spacing:2px; background:transparent; border: none;")
        v.addWidget(title)

        v.addSpacing(12)

        # Start at 0 – updated by refresh_data
        self.gauge = CircularProgress(
            value=0,
            max_value=100,
            sub_label="",
            sub_caption="no data yet",
            progress_color=ACCENT,
            track_color="#2d3748",
            size=140,
        )
        gauge_row = QHBoxLayout()
        gauge_row.addStretch()
        gauge_row.addWidget(self.gauge)
        gauge_row.addStretch()
        v.addLayout(gauge_row)

        v.addStretch()

    def update_score(self, score: int, delta_label: str = ""):
        """Update the gauge with a real productivity score 0-100."""
        self.gauge.value = score
        self.gauge.sub_label = delta_label
        self.gauge.sub_caption = "productivity" if score > 0 else "no data yet"
        self.gauge.update()


# ─────────────────────────────────────────────────────────────────────────────
#  Productive Time Card
# ─────────────────────────────────────────────────────────────────────────────

class _MiniProgressBar(QWidget):
    def __init__(self, value: int = 0, color: str = GREEN, parent=None):
        super().__init__(parent)
        self.value = value
        self.bar_color = color
        self.setFixedHeight(7)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        # Track
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#2d3748"))
        p.drawRoundedRect(0, 0, w, h, h // 2, h // 2)
        # Fill
        fill = int(w * self.value / 100)
        if fill > 0:
            # Gradient fill for a premium look
            grad = QLinearGradient(0, 0, w, 0)
            grad.setColorAt(0.0, QColor("#1d6bf3"))
            grad.setColorAt(1.0, QColor("#3fb950"))
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(0, 0, fill, h, h // 2, h // 2)
        p.end()


class ProductiveTimeCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 14px;
                border: none;
            }}
        """)
        self.setMinimumWidth(220)
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 18, 20, 18)
        v.setSpacing(0)

        # header row: title + badge
        h_row = QHBoxLayout()
        title = _lbl("PRODUCTIVE\nTIME", 9, color=TEXT_SECONDARY)
        title.setStyleSheet(
            f"color:{TEXT_SECONDARY}; letter-spacing:2px; background:transparent; border: none;")
        h_row.addWidget(title)
        h_row.addStretch()
        self._badge = QLabel("On Track")
        self._badge.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self._badge_state = "on_track"
        self._apply_badge_style()
        h_row.addWidget(self._badge)
        v.addLayout(h_row)

        v.addSpacing(16)

        # big time value
        time_row = QHBoxLayout()
        time_row.setSpacing(3)
        self.h_lbl = QLabel("0")
        self.h_lbl.setFont(QFont("Segoe UI", 38, QFont.Weight.Bold))
        self.h_lbl.setStyleSheet(f"color:{TEXT_PRIMARY}; background:transparent;")
        sub_h = _lbl("h", 16, color=TEXT_SECONDARY)
        sub_h.setStyleSheet(f"color:{TEXT_SECONDARY}; background:transparent; padding-top:16px;")
        self.m_lbl = QLabel("0")
        self.m_lbl.setFont(QFont("Segoe UI", 38, QFont.Weight.Bold))
        self.m_lbl.setStyleSheet(f"color:{TEXT_PRIMARY}; background:transparent;")
        sub_m = _lbl("m", 16, color=TEXT_SECONDARY)
        sub_m.setStyleSheet(f"color:{TEXT_SECONDARY}; background:transparent; padding-top:16px;")
        time_row.addWidget(self.h_lbl)
        time_row.addWidget(sub_h)
        time_row.addSpacing(6)
        time_row.addWidget(self.m_lbl)
        time_row.addWidget(sub_m)
        time_row.addStretch()
        v.addLayout(time_row)

        v.addSpacing(14)

        # progress bar
        self._bar = _MiniProgressBar(value=0, color=GREEN)
        v.addWidget(self._bar)

        v.addSpacing(8)

        self._goal_lbl = _lbl("Goal: 7h 00m", 10, color=TEXT_MUTED)
        v.addWidget(self._goal_lbl)

        v.addStretch()

    def update_time(self, seconds: float):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        self.h_lbl.setText(str(h))
        self.m_lbl.setText(str(m))
        # Update progress bar (goal = 7h = 25200s)
        pct = min(int(seconds / 25200 * 100), 100)
        self._bar.value = pct
        self._bar.update()
        # Update badge colour
        if pct >= 100:
            self._badge_state = "goal_met"
            self._apply_badge_style()
        elif pct >= 60:
            self._badge_state = "on_track"
            self._apply_badge_style()
        else:
            self._badge_state = "keep_going"
            self._apply_badge_style()

    def _apply_badge_style(self):
        compact = self.width() < 260
        font_size = 8 if compact else 9
        padding = "2px 6px" if compact else "3px 9px"

        if self._badge_state == "goal_met":
            text = "Goal Met" if compact else "Goal Met 🎉"
            fg = GREEN
            bg = "#1a3326"
        elif self._badge_state == "keep_going":
            text = "Keep Going"
            fg = YELLOW
            bg = "#2d2510"
        else:
            text = "On Track"
            fg = GREEN
            bg = "#1a3326"

        self._badge.setText(text)
        self._badge.setStyleSheet(
            f"color:{fg}; background:{bg}; border-radius:6px; padding:{padding};"
            f"font-size:{font_size}px; font-weight:700;"
        )

    def resizeEvent(self, event):
        compact = self.width() < 260
        value_font = 30 if compact else 38
        sub_font = 13 if compact else 16
        top_pad = 11 if compact else 16

        self.h_lbl.setFont(QFont("Segoe UI", value_font, QFont.Weight.Bold))
        self.m_lbl.setFont(QFont("Segoe UI", value_font, QFont.Weight.Bold))
        for child in self.findChildren(QLabel):
            if child.text() in {"h", "m"}:
                child.setStyleSheet(
                    f"color:{TEXT_SECONDARY}; background:transparent; padding-top:{top_pad}px; font-size:{sub_font}px;"
                )
        self._apply_badge_style()
        super().resizeEvent(event)


# ─────────────────────────────────────────────────────────────────────────────
#  Active Session Card  (blue background, live timer)
# ─────────────────────────────────────────────────────────────────────────────

class _PulsingDot(QWidget):
    """A pulsing animated red dot indicating a live session."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._alpha = 255
        self._growing = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._pulse)
        self._timer.start(40)

    def _pulse(self):
        step = 8
        if self._growing:
            self._alpha = min(255, self._alpha + step)
            if self._alpha >= 255:
                self._growing = False
        else:
            self._alpha = max(60, self._alpha - step)
            if self._alpha <= 60:
                self._growing = True
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor("#f87171")
        c.setAlpha(self._alpha)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawEllipse(1, 1, 10, 10)
        p.end()


class ActiveSessionCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {ACTIVE_CARD};
                border: none;
                border-radius: 14px;
            }}
        """)
        self.setMinimumWidth(240)

        self._seconds = 0
        self._build()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    def _tick(self):
        self._seconds += 1
        h = self._seconds // 3600
        m = (self._seconds % 3600) // 60
        s = self._seconds % 60
        self._timer_lbl.setText(f"{h:02d}:{m:02d}:{s:02d}")

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 22, 24, 22)
        v.setSpacing(0)

        # dot + label row
        dot_row = QHBoxLayout()
        dot_row.setSpacing(6)
        self._dot = _PulsingDot()
        dot_row.addWidget(self._dot)
        sess_lbl = _lbl("ACTIVE SESSION", 9, color="rgba(255,255,255,0.75)")
        sess_lbl.setStyleSheet(
            "color:rgba(255,255,255,0.75); letter-spacing:2px; background:transparent;")
        dot_row.addWidget(sess_lbl)
        dot_row.addStretch()
        v.addLayout(dot_row)

        v.addSpacing(14)

        # session name
        self.name_lbl = QLabel("Awaiting Activity…")
        self.name_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.name_lbl.setStyleSheet("color:white; background:transparent;")
        self.name_lbl.setWordWrap(True)
        v.addWidget(self.name_lbl)

        v.addSpacing(6)

        self._cat_lbl = _lbl("", 11, color="rgba(255,255,255,0.6)")
        self._cat_lbl.setStyleSheet("color:rgba(255,255,255,0.6); background:transparent;")
        v.addWidget(self._cat_lbl)

        v.addSpacing(16)

        # timer
        self._timer_lbl = QLabel("00:00:00")
        self._timer_lbl.setFont(QFont("Courier New", 28, QFont.Weight.Bold))
        self._timer_lbl.setStyleSheet("color:white; background:transparent;")
        v.addWidget(self._timer_lbl)

        v.addStretch()

    def update_session(self, app_name: str, title: str, category: str):
        if len(title) > 35:
            title = title[:32] + "..."
        self.name_lbl.setText(title)
        self._cat_lbl.setText(f"● {category.title()}" if category else "")
        self._seconds = 0


# ─────────────────────────────────────────────────────────────────────────────
#  Right Panel  – real-time stats / empty state when no project
# ─────────────────────────────────────────────────────────────────────────────

class RightStatsPanel(QFrame):
    """
    Right column widget that shows live productivity stats.
    Replaces the old dummy 'Active Project' panel.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 14px;
            }}
        """)
        self.setMinimumWidth(260)
        self.setMaximumWidth(380)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────────────
        h_row = QHBoxLayout()
        h_row.addWidget(_lbl("Today's Summary", 13, bold=True))
        h_row.addStretch()
        v.addLayout(h_row)

        v.addSpacing(18)
        v.addWidget(_divider())
        v.addSpacing(14)

        # ── Productivity tip ─────────────────────────────────────────────────
        tip_frame = QFrame()
        tip_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {ACCENT}18;
                border: 1px solid {ACCENT}44;
                border-radius: 10px;
            }}
        """)
        tip_v = QVBoxLayout(tip_frame)
        tip_v.setContentsMargins(14, 12, 14, 12)
        tip_v.setSpacing(5)

        tip_title_row = QHBoxLayout()
        tip_icon = QLabel("💡")
        tip_icon.setStyleSheet("background:transparent; font-size:14px;")
        tip_title_row.addWidget(tip_icon)
        tip_title_row.addSpacing(6)
        tip_title = _lbl("Daily Tip", 11, bold=True, color=ACCENT)
        tip_title_row.addWidget(tip_title)
        tip_title_row.addStretch()
        tip_v.addLayout(tip_title_row)

        self._tip_lbl = _lbl(
            "Start tracking to see your productivity insights here.",
            10, color=TEXT_SECONDARY, wrap=True,
        )
        tip_v.addWidget(self._tip_lbl)
        v.addWidget(tip_frame)

        v.addSpacing(18)

        # ── Today's category mini-stats ───────────────────────────────────────
        cat_title = _lbl("TODAY'S FOCUS", 9, color=TEXT_MUTED)
        cat_title.setStyleSheet(
            f"color:{TEXT_MUTED}; letter-spacing:2px; background:transparent;")
        v.addWidget(cat_title)
        v.addSpacing(10)

        self._cat_layout = QVBoxLayout()
        self._cat_layout.setSpacing(8)
        v.addLayout(self._cat_layout)

        # Placeholder rows until real data arrives
        self._empty_label = _lbl(
            "No sessions recorded yet.\nStart working to see your breakdown.",
            11, color=TEXT_MUTED, wrap=True,
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cat_layout.addWidget(self._empty_label)

        v.addSpacing(18)
        v.addWidget(_divider())
        v.addSpacing(14)

        # ── Focus trend ───────────────────────────────────────────────────────
        trend_row = QHBoxLayout()
        trend_row.addWidget(_lbl("FOCUS TREND (TODAY)", 9, color=TEXT_MUTED))
        trend_row.addStretch()
        self._trend_badge = _lbl("—", 9, bold=True, color=TEXT_SECONDARY)
        trend_row.addWidget(self._trend_badge)
        v.addLayout(trend_row)

        v.addSpacing(10)

        self._chart = MiniLineChart(
            data=[0],
            line_color=ACCENT,
        )
        self._chart.setFixedHeight(75)
        v.addWidget(self._chart)

        v.addStretch()

    def update_data(self, breakdown: list, total_secs: float):
        """
        breakdown: [(category, percentage, duration_secs), ...]
        """
        # Clear existing category rows
        while self._cat_layout.count():
            child = self._cat_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        color_map = {
            "coding": "#3b82f6",
            "learning": "#10b981",
            "writing": "#f59e0b",
            "communication": "#8b5cf6",
            "entertainment": "#ef4444",
            "designing": "#ec4899",
            "browsing": "#64748b",
            "meetings": "#06b6d4",
            "planning": "#8b5cf6",
            "reading": "#14b8a6",
            "unknown": "#6e7681",
        }

        if not breakdown:
            self._empty_label = _lbl(
                "No sessions recorded yet.\nStart working to see your breakdown.",
                11, color=TEXT_MUTED, wrap=True,
            )
            self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._cat_layout.addWidget(self._empty_label)
            self._trend_badge.setText("—")
            return

        for cat, pct, dur in breakdown[:5]:
            cat_lower = cat.lower()
            color = color_map.get(cat_lower, "#6e7681")
            h = int(dur // 3600)
            m = int((dur % 3600) // 60)
            time_str = f"{h}h {m}m" if h > 0 else f"{m}m"

            row = QWidget()
            row.setStyleSheet("background:transparent;")
            row_h = QHBoxLayout(row)
            row_h.setContentsMargins(0, 0, 0, 0)
            row_h.setSpacing(8)

            dot = QLabel("●")
            dot.setStyleSheet(
                f"color:{color}; font-size:9px; background:transparent;")
            row_h.addWidget(dot)

            row_h.addWidget(_lbl(cat.title(), 11))
            row_h.addStretch()
            row_h.addWidget(_lbl(time_str, 11, bold=True))

            self._cat_layout.addWidget(row)

        # Update tip based on breakdown
        productive_cats = {"coding", "learning", "writing", "communication", "designing", "planning", "reading", "meetings"}
        prod_pct = sum(
            pct for cat, pct, _ in breakdown
            if cat.lower() in productive_cats
        )
        if prod_pct >= 70:
            self._tip_lbl.setText(
                "Excellent focus today! You're in the top 20% of productive sessions.")
            self._trend_badge.setText("High Focus")
            self._trend_badge.setStyleSheet(f"color:{GREEN}; background:transparent;")
        elif prod_pct >= 40:
            self._tip_lbl.setText(
                "Good progress! Try to reduce distractions in the next session.")
            self._trend_badge.setText("Moderate")
            self._trend_badge.setStyleSheet(f"color:{YELLOW}; background:transparent;")
        else:
            self._tip_lbl.setText(
                "You've been spending time on non-productive activities. Time to refocus!")
            self._trend_badge.setText("Needs Focus")
            self._trend_badge.setStyleSheet(f"color:{DANGER}; background:transparent;")

        # Update trend chart with rough hourly data
        if len(breakdown) >= 2:
            chart_data = [pct for _, pct, _ in breakdown]
            self._chart.data = chart_data
            self._chart.update()


# ─────────────────────────────────────────────────────────────────────────────
#  Activity Timeline
# ─────────────────────────────────────────────────────────────────────────────

class _TimelineRow(QWidget):
    def __init__(
        self,
        time_range: str,
        task: str,
        category: str,
        duration: str,
        accent: str,
        is_active: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        bg = BG_CARD_ALT if is_active else "transparent"
        border_style = (
            f"border: 1px dashed {ACCENT}; border-radius:10px; background:{BG_CARD_ALT};"
            if is_active else
            f"border:none; background:transparent;"
        )
        self.setStyleSheet(border_style)
        self.setMinimumHeight(60)

        h = QHBoxLayout(self)
        h.setContentsMargins(8, 8, 12, 8)
        h.setSpacing(0)

        # coloured left accent bar
        bar = QFrame()
        bar.setFixedSize(4, 36)
        bar.setStyleSheet(
            f"background:{accent}; border-radius:2px; border:none;")
        h.addWidget(bar)
        h.addSpacing(14)

        # time range
        time_lbl = _lbl(time_range, 11, color=TEXT_SECONDARY)
        time_lbl.setFixedWidth(130)
        h.addWidget(time_lbl)

        # task + category
        info_col = QVBoxLayout()
        info_col.setSpacing(3)
        task_lbl = _lbl(task, 13, bold=True)
        info_col.addWidget(task_lbl)

        if is_active:
            cat_row = QHBoxLayout()
            cat_row.setSpacing(4)
            cat_row.addWidget(_lbl(category, 11, color=ACCENT))
            dot = QLabel("●")
            dot.setStyleSheet("color:#3b82f6; font-size:8px; background:transparent;")
            cat_row.addWidget(dot)
            cat_row.addStretch()
            info_col.addLayout(cat_row)
        else:
            info_col.addWidget(_lbl(category, 11, color=accent))

        h.addLayout(info_col)
        h.addStretch()

        # duration badge
        dur_badge = QFrame()
        dur_badge.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD_ALT};
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}
        """)
        dur_h = QHBoxLayout(dur_badge)
        dur_h.setContentsMargins(10, 5, 10, 5)
        dur_h.setSpacing(5)
        clock_lbl = QLabel("⏱")
        clock_lbl.setStyleSheet("background:transparent; font-size:11px;")

        if is_active:
            clock_lbl.setStyleSheet(f"background:transparent; font-size:11px; color:{ACCENT};")

        dur_h.addWidget(clock_lbl)
        dur_h.addWidget(_lbl(duration, 11))
        h.addWidget(dur_badge)


class _EmptyTimeline(QWidget):
    """Shown when there is no session data yet."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        v = QVBoxLayout(self)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.setSpacing(8)
        v.setContentsMargins(20, 30, 20, 30)

        icon = QLabel("🕐")
        icon.setStyleSheet("background:transparent; font-size:30px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(icon)

        msg = _lbl(
            "No activity recorded yet for today.\nStart working and your sessions will appear here.",
            11, color=TEXT_MUTED, wrap=True,
        )
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(msg)


class ActivityTimeline(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.time_frame = "day"
        self.on_time_frame_changed = None # Callback
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
        v.setContentsMargins(20, 18, 20, 18)
        v.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        h_row = QHBoxLayout()
        icon = QLabel("🕐")
        icon.setStyleSheet("background:transparent; font-size:14px;")
        h_row.addWidget(icon)
        h_row.addSpacing(8)
        h_row.addWidget(_lbl("Activity Timeline", 14, bold=True))
        h_row.addStretch()

        self._tabs = []
        for tab_text, tf in [("Today", "day"), ("Week", "week")]:
            tab = QPushButton(tab_text)
            tab.setFont(QFont("Segoe UI", 11))
            tab.setFixedSize(60, 28)
            tab.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Using partial or lambda properly
            tab.clicked.connect(lambda checked, t=tf: self._set_time_frame(t))
            self._tabs.append((tf, tab))
            h_row.addWidget(tab)
            
        self._update_tab_styles()

        v.addLayout(h_row)
        v.addSpacing(16)

        # ── Column headers ─────────────────────────────────────────────────────
        cols = QHBoxLayout()
        cols.setContentsMargins(26, 0, 12, 0)
        cols.addWidget(_lbl("TIME", 9, color=TEXT_MUTED))
        cols.addSpacing(94)
        cols.addWidget(_lbl("TASK", 9, color=TEXT_MUTED))
        cols.addStretch()
        cols.addWidget(_lbl("DURATION", 9, color=TEXT_MUTED))
        v.addLayout(cols)

        v.addSpacing(8)
        v.addWidget(_divider())
        v.addSpacing(10)

        # ── Session rows container ─────────────────────────────────────────────
        self.rows_layout = QVBoxLayout()
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(2)
        v.addLayout(self.rows_layout)

        # Start with empty state
        self._empty = _EmptyTimeline()
        self.rows_layout.addWidget(self._empty)

        v.addStretch()

    def update_timeline(self, timeline_data: list):
        # Remove old rows
        while self.rows_layout.count():
            child = self.rows_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not timeline_data:
            self._empty = _EmptyTimeline()
            self.rows_layout.addWidget(self._empty)
            return

        for item in timeline_data:
            row = _TimelineRow(
                time_range=item.get("time_range", ""),
                task=item.get("task", ""),
                category=item.get("category", ""),
                duration=item.get("duration", ""),
                accent=item.get("color", "#3b82f6"),
                is_active=item.get("is_active", False)
            )
            self.rows_layout.addWidget(row)

    def _set_time_frame(self, tf: str):
        self.time_frame = tf
        self._update_tab_styles()
        if self.on_time_frame_changed:
            self.on_time_frame_changed()

    def _update_tab_styles(self):
        for tf, tab in self._tabs:
            if self.time_frame == tf:
                tab.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {ACCENT};
                        color: white;
                        border-radius: 8px;
                        border: none;
                        font-weight: 600;
                    }}
                """)
            else:
                tab.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {TEXT_SECONDARY};
                        border: none;
                        border-radius: 8px;
                    }}
                    QPushButton:hover {{
                        color: {TEXT_PRIMARY};
                    }}
                """)


# ─────────────────────────────────────────────────────────────────────────────
#  Bottom Stat Cards
# ─────────────────────────────────────────────────────────────────────────────

class _StatCard(QFrame):
    def __init__(
        self,
        icon: str,
        icon_color: str,
        label: str,
        value: str,
        sub: str,
        sub_color: str = TEXT_SECONDARY,
        parent=None,
    ):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 14px;
            }}
        """)
        self.setFixedHeight(90)
        self._build(icon, icon_color, label, value, sub, sub_color)

    def _build(self, icon, icon_color, label, value, sub, sub_color):
        h = QHBoxLayout(self)
        h.setContentsMargins(18, 0, 18, 0)
        h.setSpacing(14)

        # icon circle
        ic_lbl = QLabel(icon)
        ic_lbl.setFixedSize(36, 36)
        ic_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic_lbl.setFont(QFont("Segoe UI", 16))
        ic_lbl.setStyleSheet(f"""
            background-color: {icon_color}22;
            border-radius: 10px;
            color: {icon_color};
        """)
        h.addWidget(ic_lbl)

        info = QVBoxLayout()
        info.setSpacing(4)
        info.addWidget(_lbl(label, 10, color=TEXT_MUTED))

        val_row = QHBoxLayout()
        val_row.setSpacing(8)
        self.val_lbl = _lbl(value, 20, bold=True)
        self.sub_lbl = _lbl(sub, 11, color=sub_color)
        val_row.addWidget(self.val_lbl)
        val_row.addWidget(self.sub_lbl)
        val_row.addStretch()
        info.addLayout(val_row)
        h.addLayout(info)
        h.addStretch()

    def update_stat(self, value: str, sub: str = None):
        self.val_lbl.setText(value)
        if sub is not None:
            self.sub_lbl.setText(sub)


# ─────────────────────────────────────────────────────────────────────────────
#  Dashboard Page  (assembles everything)
# ─────────────────────────────────────────────────────────────────────────────

class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color:{BG_MAIN};")
        self._right_panel: RightStatsPanel | None = None
        self._engine = None # Reference to engine for refresh
        self._body_layout = None
        self._cards_row = None
        self._stats_row = None
        self._left_layout = None
        self._alert_btn = None
        self._mini_btn = None
        self._build()

    def _build(self):
        # Outer scroll area so the dashboard is scrollable if window is small
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

        # ── Top header bar ────────────────────────────────────────────────────
        root.addLayout(self._build_header())
        root.addSpacing(24)

        # ── Main body: left content + right stats panel ───────────────────────
        body = QHBoxLayout()
        body.setSpacing(20)

        # left section
        left = QVBoxLayout()
        left.setSpacing(16)

        # --- cards row ---
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        self.focus_card = FocusScoreCard()
        self.prod_card = ProductiveTimeCard()
        self.active_card = ActiveSessionCard()
        for card in (self.focus_card, self.prod_card, self.active_card):
            apply_soft_shadow(card)
        cards_row.addWidget(self.focus_card)
        cards_row.addWidget(self.prod_card)
        cards_row.addWidget(self.active_card)
        left.addLayout(cards_row)

        # --- timeline ---
        self.timeline = ActivityTimeline()
        apply_soft_shadow(self.timeline)
        self.timeline.on_time_frame_changed = lambda: self.refresh_data(self._engine) if self._engine else None
        left.addWidget(self.timeline)

        # --- bottom stats ---
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)
        self.stat_switches = _StatCard("📂", ORANGE, "App Switches", "0",   "Today",       GREEN)
        self.stat_idle     = _StatCard("⊙",  "#6e7681", "Idle Time",  "0m", "Total",   TEXT_SECONDARY)
        self.stat_deep     = _StatCard("💡", ACCENT,   "Deep Work",   "0m", "Focus",   TEXT_SECONDARY)
        for card in (self.stat_switches, self.stat_idle, self.stat_deep):
            apply_soft_shadow(card, blur_radius=24, offset_y=5, alpha=60)
        stats_row.addWidget(self.stat_switches)
        stats_row.addWidget(self.stat_idle)
        stats_row.addWidget(self.stat_deep)
        left.addLayout(stats_row)

        body.addLayout(left, stretch=3)

        # right panel  ← replaces the dummy ActiveProjectPanel
        self._right_panel = RightStatsPanel()
        apply_soft_shadow(self._right_panel, blur_radius=30, offset_y=8, alpha=76)
        body.addWidget(self._right_panel, stretch=0)

        root.addLayout(body)
        self._body_layout = body
        self._cards_row = cards_row
        self._stats_row = stats_row
        self._left_layout = left
        self._apply_responsive_layout()

    def refresh_data(self, engine):
        """Called to dynamically fetch DB metrics into dashboard widgets."""
        if not engine:
            return

        self._engine = engine
        
        # 1. Total Time
        secs = engine.get_total_time("day")
        self.prod_card.update_time(secs)

        # 2. Timeline
        tl_data = engine.get_timeline_data(self.timeline.time_frame)
        if self.timeline.time_frame == "week":
            self.timeline.update_timeline(self._build_weekly_timeline_rows(tl_data))
        else:
            self.timeline.update_timeline(tl_data[-8:])  # Last 8 sessions for today view

        # 3. Category breakdown → Focus Score + Right Panel
        breakdown = engine.get_category_breakdown("day")

        productive_cats = {"coding", "learning", "writing", "communication"}
        productive_secs = sum(
            dur for cat, pct, dur in breakdown
            if cat.lower() in productive_cats
        )
        total_secs_bd = sum(dur for _, _, dur in breakdown)
        if total_secs_bd > 0:
            score = int(productive_secs / total_secs_bd * 100)
        else:
            score = 0
        self.focus_card.update_score(score)

        # Update right panel
        if self._right_panel:
            self._right_panel.update_data(breakdown, secs)

        # 4. Deep work stat
        deep = productive_secs
        h = int(deep // 3600)
        m = int((deep % 3600) // 60)
        self.stat_deep.update_stat(f"{h}h {m}m" if h > 0 else f"{m}m")
        
        # 5. App Switches
        switches = engine.get_app_switches("day")
        self.stat_switches.update_stat(str(switches))

        # 6. Idle time
        idle = engine.get_idle_time("day")
        ih = int(idle // 3600)
        im = int((idle % 3600) // 60)
        self.stat_idle.update_stat(f"{ih}h {im}m" if ih > 0 else f"{im}m")

    def _build_weekly_timeline_rows(self, tl_data: list) -> list:
        """
        Build a per-day summary for the Week tab so it is meaningfully different
        from the Today tab's per-session timeline.
        """
        if not tl_data:
            return []

        daily = {}
        today_iso = datetime.date.today().isoformat()

        for item in tl_data:
            date_str = item.get("date")
            if not date_str:
                continue

            if date_str not in daily:
                daily[date_str] = {
                    "sessions": 0,
                    "minutes": 0,
                    "category_minutes": {},
                    "color": item.get("color", "#6e7681"),
                }

            daily[date_str]["sessions"] += 1
            mins = self._duration_to_minutes(item.get("duration", "0m"))
            daily[date_str]["minutes"] += mins

            cat = item.get("category", "Unknown")
            cat_map = daily[date_str]["category_minutes"]
            cat_map[cat] = cat_map.get(cat, 0) + mins

        rows = []
        for date_str in sorted(daily.keys()):
            info = daily[date_str]
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            top_cat = max(
                info["category_minutes"].items(),
                key=lambda x: x[1],
            )[0] if info["category_minutes"] else "Unknown"

            h = info["minutes"] // 60
            m = info["minutes"] % 60
            dur_str = f"{h}h {m}m" if h > 0 else f"{max(1, m)}m"

            rows.append({
                "time_range": date_obj.strftime("%a, %d %b"),
                "task": f"{info['sessions']} session{'s' if info['sessions'] != 1 else ''}",
                "category": f"Top: {top_cat}",
                "duration": dur_str,
                "color": info["color"],
                "is_active": date_str == today_iso,
            })

        return rows

    @staticmethod
    def _duration_to_minutes(duration: str) -> int:
        """
        Convert a compact duration like '2h 15m' or '45m' to minutes.
        """
        text = (duration or "").strip().lower()
        if not text:
            return 0

        hours = 0
        minutes = 0

        if "h" in text:
            try:
                hours = int(text.split("h")[0].strip())
            except ValueError:
                hours = 0
            text = text.split("h", 1)[1].strip()

        if "m" in text:
            try:
                minutes = int(text.replace("m", "").strip() or "0")
            except ValueError:
                minutes = 0

        return max(0, hours * 60 + minutes)

    # ── top header ────────────────────────────────────────────────────────────
    def _build_header(self) -> QHBoxLayout:
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

        # Dynamic greeting
        greet = _get_greeting()
        greet_col = QVBoxLayout()
        greet_col.setSpacing(4)
        greet_col.addWidget(_lbl(f"{greet}, Alex", 20, bold=True))
        greet_col.addWidget(
            _lbl("Here's your productivity overview for today.", 12,
                 color=TEXT_SECONDARY))
        h.addLayout(greet_col)
        h.addStretch()

        # ── Attention alert button ────────────────────────────────────────────
        self._alert_btn = QPushButton("⚠  Attention Needed")
        self._alert_btn.setFixedHeight(36)
        self._alert_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        self._alert_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._alert_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #78350f;
                color: #fbbf24;
                border: 1px solid #b45309;
                border-radius: 10px;
                padding: 0 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #92400e;
                color: #fcd34d;
            }}
        """)
        self._alert_btn.clicked.connect(self._show_attention_dialog)
        h.addSpacing(10)
        h.addWidget(self._alert_btn)

        # ── Show Mini Tracker button ──────────────────────────────────────────────
        self._mini_btn = QPushButton("🕒  Mini Tracker")
        self._mini_btn.setFixedHeight(36)
        self._mini_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        self._mini_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mini_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 0 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #2563eb;
            }}
        """)
        self._mini_btn.clicked.connect(self._show_mini_tracker)
        h.addSpacing(10)
        h.addWidget(self._mini_btn)

        # ── icon buttons (bell + settings) ───────────────────────────────────
        for icon_text, callback in [
            ("🔔", None),
            ("⚙", self._open_settings),
        ]:
            btn = QPushButton(icon_text)
            btn.setFixedSize(36, 36)
            btn.setFont(QFont("Segoe UI", 16))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {BG_CARD};
                    border: 1px solid {BORDER};
                    border-radius: 10px;
                    color: {TEXT_SECONDARY};
                }}
                QPushButton:hover {{
                    background-color: {BG_CARD_ALT};
                    color: {TEXT_PRIMARY};
                }}
            """)
            if callback:
                btn.clicked.connect(callback)
            h.addSpacing(10)
            h.addWidget(btn)

        return h

    def _show_attention_dialog(self):
        """Open the Attention Needed modal overlay."""
        top = self.window()
        dlg = show_attention_dialog(
            parent=top,
            task_name="Productivity Alert",
            warning_message=(
                "You've been spending a lot of time on non-productive activities. "
                "Consider closing distracting apps and refocusing on your work."
            ),
        )
        dlg.exec()

    def _show_mini_tracker(self):
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if hasattr(app, 'mini_tracker') and app.mini_tracker:
            app.mini_tracker.show()
            app.mini_tracker.raise_()
            app.mini_tracker.activateWindow()

    def _toggle_sidebar(self):
        main_win = self.window()
        if hasattr(main_win, '_sidebar'):
            main_win._sidebar.toggle_sidebar()

    def resizeEvent(self, event):
        self._apply_responsive_layout()
        super().resizeEvent(event)

    def _apply_responsive_layout(self):
        w = self.width()
        if not self._body_layout or not self._cards_row or not self._stats_row:
            return

        # Main dashboard body: side-by-side on wide screens, stacked on narrow screens.
        if w < 1180:
            self._body_layout.setDirection(QBoxLayout.Direction.TopToBottom)
            if self._right_panel:
                self._right_panel.setMaximumWidth(16777215)
                self._right_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        else:
            self._body_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            if self._right_panel:
                self._right_panel.setMaximumWidth(380)
                self._right_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        # Cards and bottom stats rows: stack if there is not enough room.
        row_dir = QBoxLayout.Direction.TopToBottom if w < 1080 else QBoxLayout.Direction.LeftToRight
        self._cards_row.setDirection(row_dir)
        self._stats_row.setDirection(row_dir)

        # Compact header actions on small widths.
        if self._alert_btn and self._mini_btn:
            if w < 980:
                self._alert_btn.setText("⚠  Alert")
                self._mini_btn.setText("🕒  Mini")
            else:
                self._alert_btn.setText("⚠  Attention Needed")
                self._mini_btn.setText("🕒  Mini Tracker")

    def _open_settings(self):
        main_win = self.window()
        if hasattr(main_win, "_sidebar"):
            main_win._sidebar.set_active_index(4)
