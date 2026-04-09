from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QFontMetrics


class CircularProgress(QWidget):
    """
    Speedometer-style circular gauge.
    Arc spans 270° (from bottom-left clockwise over the top to bottom-right).
    """

    def __init__(
        self,
        value: int = 85,
        max_value: int = 100,
        label: str = "",
        sub_label: str = "+12%",
        sub_caption: str = "vs. yesterday",
        track_color: str = "#2d3748",
        progress_color: str = "#1d6bf3",
        size: int = 130,
        parent=None,
    ):
        super().__init__(parent)
        self.value = value
        self.max_value = max_value
        self.label = label
        self.sub_label = sub_label
        self.sub_caption = sub_caption
        self.track_color = track_color
        self.progress_color = progress_color
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    # ── public helpers ────────────────────────────────────────────────────────
    def set_value(self, value: int):
        self.value = max(0, min(value, self.max_value))
        self.update()

    # ── painting ──────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        margin = 12
        arc_size = min(w, h) - margin * 2
        arc_x = (w - arc_size) // 2
        arc_y = (h - arc_size) // 2
        rect = QRect(arc_x, arc_y, arc_size, arc_size)

        pen_width = 9

        # ── 1. Grey track (full 270°, clockwise) ──────────────────────────────
        pen = QPen(QColor(self.track_color))
        pen.setWidth(pen_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        # In Qt: startAngle at 225° (CCW from 3-o-clock), span -270° (CW)
        painter.drawArc(rect, 225 * 16, -270 * 16)

        # ── 2. Coloured progress arc ──────────────────────────────────────────
        pen.setColor(QColor(self.progress_color))
        painter.setPen(pen)
        filled_span = int(-(self.value / self.max_value) * 270 * 16)
        painter.drawArc(rect, 225 * 16, filled_span)

        # ── 3. Centre value text ──────────────────────────────────────────────
        painter.setPen(QColor("#e6edf3"))
        font = QFont("Segoe UI", int(arc_size * 0.22), QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect.adjusted(0, -6, 0, -6), Qt.AlignmentFlag.AlignCenter, str(self.value))

        # ── 4. Sub-label (e.g. "+12%") ────────────────────────────────────────
        if self.sub_label:
            sub_font = QFont("Segoe UI", int(arc_size * 0.09), QFont.Weight.Bold)
            painter.setFont(sub_font)
            # Green up-arrow prefix
            green = "#3fb950"
            painter.setPen(QColor(green))
            sub_text = f"↑ {self.sub_label}"
            fm = QFontMetrics(sub_font)
            text_w = fm.horizontalAdvance(sub_text)
            text_x = (w - text_w) // 2
            text_y = arc_y + arc_size // 2 + int(arc_size * 0.22)
            painter.drawText(QPoint(text_x, text_y), sub_text)

        # ── 5. Caption (e.g. "vs. yesterday") ────────────────────────────────
        if self.sub_caption:
            cap_font = QFont("Segoe UI", int(arc_size * 0.075))
            painter.setFont(cap_font)
            painter.setPen(QColor("#8b949e"))
            fm2 = QFontMetrics(cap_font)
            cap_w = fm2.horizontalAdvance(self.sub_caption)
            cap_x = (w - cap_w) // 2
            cap_y = arc_y + arc_size // 2 + int(arc_size * 0.36)
            painter.drawText(QPoint(cap_x, cap_y), self.sub_caption)

        painter.end()
