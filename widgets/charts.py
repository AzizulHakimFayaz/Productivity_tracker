from __future__ import annotations
import math
import datetime
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QRect, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QFont, QFontMetrics,
    QPainterPath, QLinearGradient, QBrush, QConicalGradient, QRadialGradient,
)


# ─────────────────────────────────────────────────────────────────────────────
#  Mini Line Chart  (Focus Trend panel)
# ─────────────────────────────────────────────────────────────────────────────
class MiniLineChart(QWidget):
    """
    Small smooth line chart used inside the Active-Project / Focus-Trend panel.
    Draws a gradient-filled area below the line plus a terminal dot.
    """

    def __init__(
        self,
        data: list[float] | None = None,
        line_color: str = "#1d6bf3",
        parent=None,
    ):
        super().__init__(parent)
        self.data = data or [30, 45, 35, 60, 50, 72, 58, 80, 68, 90, 85, 95]
        self.line_color = line_color
        self.setMinimumHeight(75)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_data(self, data: list[float]):
        self.data = data
        self.update()

    def paintEvent(self, event):
        if len(self.data) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        pad_x, pad_top, pad_bot = 6, 8, 8

        min_v = min(self.data)
        max_v = max(self.data)
        rng = max_v - min_v or 1

        def to_pt(i: int, v: float) -> QPointF:
            x = pad_x + i / (len(self.data) - 1) * (w - pad_x * 2)
            y = pad_top + (1 - (v - min_v) / rng) * (h - pad_top - pad_bot)
            return QPointF(x, y)

        points = [to_pt(i, v) for i, v in enumerate(self.data)]

        # ── Build smooth path via cubic bezier ───────────────────────────────
        path = QPainterPath()
        path.moveTo(points[0])
        for i in range(1, len(points)):
            p0 = points[i - 1]
            p1 = points[i]
            ctrl_x = (p0.x() + p1.x()) / 2
            path.cubicTo(QPointF(ctrl_x, p0.y()), QPointF(ctrl_x, p1.y()), p1)

        # ── Gradient fill area ────────────────────────────────────────────────
        fill_path = QPainterPath(path)
        fill_path.lineTo(points[-1].x(), h)
        fill_path.lineTo(points[0].x(), h)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, pad_top, 0, h)
        c = QColor(self.line_color)
        c.setAlpha(60)
        grad.setColorAt(0.0, c)
        c.setAlpha(0)
        grad.setColorAt(1.0, c)
        painter.fillPath(fill_path, QBrush(grad))

        # ── Line stroke ───────────────────────────────────────────────────────
        pen = QPen(QColor(self.line_color), 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)

        # ── Terminal dot ──────────────────────────────────────────────────────
        last = points[-1]
        painter.setPen(Qt.PenStyle.NoPen)
        # Halo
        halo = QColor(self.line_color)
        halo.setAlpha(50)
        painter.setBrush(halo)
        painter.drawEllipse(last, 6.0, 6.0)
        # Core
        painter.setBrush(QColor(self.line_color))
        painter.drawEllipse(last, 3.5, 3.5)
        # White centre
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(last, 1.5, 1.5)

        painter.end()


# ─────────────────────────────────────────────────────────────────────────────
#  Donut Chart  (Analytics – Total Active Time)
# ─────────────────────────────────────────────────────────────────────────────
class DonutChart(QWidget):
    """
    Donut / ring chart.  Accepts a list of (label, value, hex_color) tuples.
    Renders with a thick ring and the total label centred.
    """

    def __init__(
        self,
        segments: list[tuple[str, float, str]] | None = None,
        center_text: str = "6h 12m",
        center_sub: str = "Total Time",
        size: int = 180,
        thickness: int = 28,
        parent=None,
    ):
        super().__init__(parent)
        self.segments = segments or [
            ("Productivity", 40, "#8b5cf6"),
            ("Writing",      30, "#3b82f6"),
            ("Browsing",     15, "#1d6bf3"),
            ("Entertainment",10, "#6e7681"),
            ("Messaging",     3, "#374151"),
        ]
        self.center_text = center_text
        self.center_sub  = center_sub
        self.ring_thick  = thickness
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        margin = self.ring_thick + 4
        rect = QRectF(margin, margin, w - margin * 2, h - margin * 2)

        total = sum(s[1] for s in self.segments) or 1
        start_angle = 90 * 16   # start at 12-o-clock

        pen = QPen()
        pen.setWidth(self.ring_thick)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)

        gap = 3 * 16   # tiny gap between segments (in Qt angle units)

        for _label, value, color in self.segments:
            span = int(value / total * 360 * 16)
            pen.setColor(QColor(color))
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(rect, start_angle, -(span - gap))
            start_angle -= span

        # ── Centre text ───────────────────────────────────────────────────────
        painter.setPen(QColor("#e6edf3"))
        font = QFont("Segoe UI", 18, QFont.Weight.Bold)
        painter.setFont(font)
        text_rect = QRect(0, int(h / 2) - 22, w, 26)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter, self.center_text)

        font2 = QFont("Segoe UI", 9)
        painter.setFont(font2)
        painter.setPen(QColor("#8b949e"))
        sub_rect = QRect(0, int(h / 2) + 8, w, 18)
        painter.drawText(sub_rect, Qt.AlignmentFlag.AlignHCenter, self.center_sub)

        painter.end()


# ─────────────────────────────────────────────────────────────────────────────
#  Timeline Bar Chart  (Analytics – Activity Timeline)
#  Supports day / week / month / year rendering modes
# ─────────────────────────────────────────────────────────────────────────────
class TimelineBarChart(QWidget):
    """
    Horizontal-axis time chart.
    - Day:   AM → PM timeline with session bars
    - Week:  Mon–Sun vertical bars showing daily totals
    - Month: 1–31 vertical bars showing daily totals
    - Year:  Jan–Dec vertical bars showing monthly totals
    """

    def __init__(
        self,
        sessions: list[dict] | None = None,
        time_frame: str = "day",
        parent=None,
    ):
        super().__init__(parent)
        self.sessions = sessions or []
        self.time_frame = time_frame
        self.hour_start = 9
        self.hour_end   = 21
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    @staticmethod
    def _parse_duration_mins(dur_str: str) -> float:
        """Parse duration strings like '2h 30m' or '45m' into minutes."""
        mins = 0.0
        if "h" in dur_str and "m" in dur_str:
            parts = dur_str.split("h")
            try:
                mins = int(parts[0].strip()) * 60 + int(parts[1].replace("m", "").strip())
            except ValueError:
                pass
        elif "h" in dur_str:
            try:
                mins = int(dur_str.replace("h", "").strip()) * 60
            except ValueError:
                pass
        elif "m" in dur_str:
            try:
                mins = int(dur_str.replace("m", "").strip())
            except ValueError:
                pass
        return mins

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.time_frame == "day":
            self._paint_day(painter)
        elif self.time_frame == "week":
            self._paint_week(painter)
        elif self.time_frame == "month":
            self._paint_month(painter)
        elif self.time_frame == "year":
            self._paint_year(painter)
        else:
            self._paint_day(painter)

        painter.end()

    # ── Day view: horizontal timeline (AM → PM) ──────────────────────────────
    def _paint_day(self, painter: QPainter):
        w = self.width()
        h = self.height()
        pad_l, pad_r  = 8, 8
        pad_top, pad_bot = 10, 28
        chart_w = w - pad_l - pad_r
        chart_h = h - pad_top - pad_bot

        hour_range = self.hour_end - self.hour_start

        def hour_to_x(hour: float) -> float:
            return pad_l + (hour - self.hour_start) / hour_range * chart_w

        # Background area
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#21262d"))
        painter.drawRoundedRect(pad_l, pad_top, chart_w, chart_h, 6, 6)

        # Vertical grid lines
        grid_pen = QPen(QColor("#30363d"), 1, Qt.PenStyle.SolidLine)
        painter.setPen(grid_pen)
        for hour in range(self.hour_start, self.hour_end + 1):
            x = int(hour_to_x(hour))
            painter.drawLine(x, pad_top, x, pad_top + chart_h)

        # Session bars
        bar_h = chart_h - 4
        for s in self.sessions:
            x1 = hour_to_x(s["start"])
            x2 = hour_to_x(s["end"])
            bw = max(x2 - x1, 3)
            color = QColor(s["color"])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(x1, pad_top + 2, bw, bar_h), 3, 3)

        # X-axis hour labels
        lbl_font = QFont("Segoe UI", 8)
        painter.setFont(lbl_font)
        painter.setPen(QColor("#6e7681"))
        fm = QFontMetrics(lbl_font)
        for hour in range(self.hour_start, self.hour_end + 1, 1):
            if hour == self.hour_start or hour % 2 == 0:
                if hour < 12:
                    lbl = f"{hour} AM"
                elif hour == 12:
                    lbl = "12 PM"
                else:
                    lbl = f"{hour - 12} PM"
                x = int(hour_to_x(hour))
                lw = fm.horizontalAdvance(lbl)
                ly = h - 6
                painter.drawText(x - lw // 2, ly, lbl)

    # ── Week view: Mon–Sun bars ──────────────────────────────────────────────
    def _paint_week(self, painter: QPainter):
        labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        day_totals = [0.0] * 7
        day_colors = [[] for _ in range(7)]

        for s in self.sessions:
            dow = s.get("day_of_week", 0)  # 0=Mon, 6=Sun
            dur = self._parse_duration_mins(s.get("duration", "0m"))
            if 0 <= dow < 7:
                day_totals[dow] += dur
                day_colors[dow].append(s.get("color", "#6366f1"))

        self._paint_vertical_bars(painter, labels, day_totals, day_colors)

    # ── Month view: Day 1–31 bars ────────────────────────────────────────────
    def _paint_month(self, painter: QPainter):
        now = datetime.datetime.now()
        # Get number of days in current month
        if now.month == 12:
            days_in_month = 31
        else:
            next_month = now.replace(month=now.month + 1, day=1)
            days_in_month = (next_month - now.replace(day=1)).days

        labels = [str(d) for d in range(1, days_in_month + 1)]
        day_totals = [0.0] * days_in_month
        day_colors = [[] for _ in range(days_in_month)]

        for s in self.sessions:
            dom = s.get("day_of_month", 1) - 1  # 0-indexed
            dur = self._parse_duration_mins(s.get("duration", "0m"))
            if 0 <= dom < days_in_month:
                day_totals[dom] += dur
                day_colors[dom].append(s.get("color", "#6366f1"))

        self._paint_vertical_bars(painter, labels, day_totals, day_colors)

    # ── Year view: Jan–Dec bars ──────────────────────────────────────────────
    def _paint_year(self, painter: QPainter):
        labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        month_totals = [0.0] * 12
        month_colors = [[] for _ in range(12)]

        for s in self.sessions:
            month = s.get("month", 1) - 1  # 0-indexed
            dur = self._parse_duration_mins(s.get("duration", "0m"))
            if 0 <= month < 12:
                month_totals[month] += dur
                month_colors[month].append(s.get("color", "#6366f1"))

        self._paint_vertical_bars(painter, labels, month_totals, month_colors)

    # ── Generic vertical bar chart renderer ──────────────────────────────────
    def _paint_vertical_bars(self, painter: QPainter, labels: list[str],
                             values: list[float], colors: list[list[str]]):
        w = self.width()
        h = self.height()
        pad_l, pad_r = 8, 8
        pad_top, pad_bot = 10, 28
        chart_w = w - pad_l - pad_r
        chart_h = h - pad_top - pad_bot

        n = len(labels)
        bar_spacing = chart_w / max(n, 1)
        bar_width = max(min(bar_spacing * 0.6, 24), 3)

        # Background area
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#21262d"))
        painter.drawRoundedRect(pad_l, pad_top, chart_w, chart_h, 6, 6)

        # Vertical grid lines
        grid_pen = QPen(QColor("#30363d"), 1, Qt.PenStyle.SolidLine)
        painter.setPen(grid_pen)
        for i in range(n + 1):
            x = int(pad_l + i * bar_spacing)
            painter.drawLine(x, pad_top, x, pad_top + chart_h)

        max_val = max(values) if values and max(values) > 0 else 1.0

        # Draw bars
        for i, val in enumerate(values):
            if val > 0:
                bar_h = max(int(val / max_val * (chart_h - 6)), 2)
                x = pad_l + i * bar_spacing + (bar_spacing - bar_width) / 2
                y = pad_top + chart_h - 2 - bar_h

                # Use dominant color from sessions, or accent gradient
                painter.setPen(Qt.PenStyle.NoPen)
                grad = QLinearGradient(x, y, x, y + bar_h)
                grad.setColorAt(0, QColor("#818cf8"))
                grad.setColorAt(1, QColor("#6366f1"))
                painter.setBrush(QBrush(grad))
                painter.drawRoundedRect(QRectF(x, y, bar_width, bar_h), 3, 3)

        # X-axis labels
        lbl_font = QFont("Segoe UI", 7 if n > 12 else 8)
        painter.setFont(lbl_font)
        painter.setPen(QColor("#6e7681"))
        fm = QFontMetrics(lbl_font)

        # For month view with many labels, show every Nth label
        step = 1
        if n > 15:
            step = 5  # show every 5th day for month view

        for i, label in enumerate(labels):
            if step > 1 and i % step != 0 and i != n - 1:
                continue
            x = int(pad_l + i * bar_spacing + bar_spacing / 2)
            lw = fm.horizontalAdvance(label)
            painter.drawText(x - lw // 2, h - 6, label)


# ─────────────────────────────────────────────────────────────────────────────
#  Category Progress Bar  (Analytics – Categories list)
# ─────────────────────────────────────────────────────────────────────────────
class CategoryBar(QWidget):
    """Single horizontal progress bar for the categories list."""

    def __init__(self, percentage: float, color: str = "#8b5cf6", parent=None):
        super().__init__(parent)
        self.percentage = percentage
        self.bar_color = color
        self.setFixedHeight(5)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # Track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#30363d"))
        painter.drawRoundedRect(0, 0, w, h, h // 2, h // 2)

        # Fill
        fill_w = int(w * self.percentage / 100)
        if fill_w > 0:
            painter.setBrush(QColor(self.bar_color))
            painter.drawRoundedRect(0, 0, fill_w, h, h // 2, h // 2)

        painter.end()
