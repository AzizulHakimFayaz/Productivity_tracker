from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QPen, QLinearGradient, QPainterPath, QFontMetrics

from styles.theme import BG_CARD, ACCENT, BORDER, TEXT_PRIMARY, TEXT_MUTED, TEXT_SECONDARY


class _GradientFrame(QFrame):
    """Custom frame with painted rounded corners and subtle border glow."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 14, 14)

        # Background fill
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor("#1c2333"))
        grad.setColorAt(1.0, QColor("#161b26"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(path)

        # Border
        p.setPen(QPen(QColor("#30363d"), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        p.end()


class MiniTrackerWidget(QWidget):
    """
    A floating, frameless desktop widget that tracks live activity.
    Can be dragged anywhere and closed via the × button.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(300, 86)

        # State for dragging
        self._drag_pos = None

        # Live Session Duration Tracking
        self._current_seconds = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

        # Category colour for the accent dot
        self._cat_color = ACCENT
        self._raw_title = "Awaiting Activity…"
        self._raw_app_line = "Focus.io Tracker"

        self._build()

    def _build(self):
        # Outer translucent container
        self.container = _GradientFrame(self)
        self.container.setFixedSize(self.width(), self.height())

        layout = QHBoxLayout(self.container)
        layout.setContentsMargins(14, 10, 10, 10)
        layout.setSpacing(10)

        # ── Left accent dot (category colour) ─────────────────────────────────
        self.dot = QLabel("●")
        self.dot.setStyleSheet(
            f"color: {ACCENT}; font-size: 13px; background:transparent; border:none;")
        self.dot.setFixedWidth(14)
        layout.addWidget(self.dot)

        # ── Info column ───────────────────────────────────────────────────────
        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)
        info_layout.setContentsMargins(0, 0, 0, 0)

        self.title_lbl = QLabel("Awaiting Activity…")
        self.title_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.title_lbl.setStyleSheet(
            f"color: {TEXT_PRIMARY}; background:transparent; border:none;")

        self.app_lbl = QLabel("Focus.io Tracker")
        self.app_lbl.setFont(QFont("Segoe UI", 9))
        self.app_lbl.setStyleSheet(
            f"color: {TEXT_MUTED}; background:transparent; border:none;")

        info_layout.addWidget(self.title_lbl)
        info_layout.addWidget(self.app_lbl)
        layout.addLayout(info_layout, stretch=1)

        # ── Timer ─────────────────────────────────────────────────────────────
        timer_col = QVBoxLayout()
        timer_col.setSpacing(1)
        timer_col.setContentsMargins(0, 0, 0, 0)

        self.timer_lbl = QLabel("00:00")
        self.timer_lbl.setFont(QFont("Courier New", 13, QFont.Weight.Bold))
        self.timer_lbl.setStyleSheet(
            f"color: {ACCENT}; background:transparent; border:none;")
        self.timer_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

        self._cat_badge = QLabel("—")
        self._cat_badge.setFont(QFont("Segoe UI", 8))
        self._cat_badge.setStyleSheet(
            f"color: {TEXT_MUTED}; background:transparent; border:none;")
        self._cat_badge.setAlignment(Qt.AlignmentFlag.AlignRight)

        timer_col.addWidget(self.timer_lbl)
        timer_col.addWidget(self._cat_badge)
        layout.addLayout(timer_col)

        # ── Close button ──────────────────────────────────────────────────────
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setFont(QFont("Segoe UI", 13))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                color: {TEXT_MUTED};
                background: transparent;
                border: none;
                border-radius: 10px;
                padding: 0;
            }}
            QPushButton:hover {{
                color: #f87171;
                background: #2d1515;
            }}
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignTop)

    def _tick(self):
        self._current_seconds += 1
        m = self._current_seconds // 60
        s = self._current_seconds % 60
        self.timer_lbl.setText(f"{m:02d}:{s:02d}")

    def update_activity(self, app_name: str, title: str, domain: str, category: str):
        """Update the tracker with the newest focused window context."""
        self._raw_title = title or "Untitled"
        if domain:
            self._raw_app_line = f"{app_name}  •  {domain}"
        else:
            self._raw_app_line = app_name
        self._fit_texts()

        # Reset the timer
        self._current_seconds = 0
        self._tick()

        # Category colours and badge
        color_map = {
            "coding":        "#3b82f6",
            "learning":      "#10b981",
            "writing":       "#f59e0b",
            "communication": "#8b5cf6",
            "entertainment": "#ef4444",
            "designing":     "#ec4899",
            "browsing":      "#64748b",
            "meetings":      "#06b6d4",
            "planning":      "#8b5cf6",
            "reading":       "#14b8a6",
            "unknown":       TEXT_MUTED,
        }
        icon_map = {
            "coding":        "💻",
            "learning":      "📚",
            "writing":       "✍",
            "communication": "💬",
            "entertainment": "🎬",
            "designing":     "🎨",
            "browsing":      "🌐",
            "meetings":      "👥",
            "planning":      "📅",
            "reading":       "📖",
            "unknown":       "⊙",
        }

        c = color_map.get(category, TEXT_MUTED)
        icon = icon_map.get(category, "⊙")
        self._cat_color = c

        self.dot.setStyleSheet(
            f"color: {c}; font-size: 13px; background:transparent; border:none;")
        self.timer_lbl.setStyleSheet(
            f"color: {c}; background:transparent; border:none;")
        self._cat_badge.setText(f"{icon} {category.title()}" if category else "—")

    def _fit_texts(self):
        title_width = max(40, self.title_lbl.width())
        app_width = max(40, self.app_lbl.width())
        title_metrics = QFontMetrics(self.title_lbl.font())
        app_metrics = QFontMetrics(self.app_lbl.font())
        self.title_lbl.setText(
            title_metrics.elidedText(self._raw_title, Qt.TextElideMode.ElideRight, title_width)
        )
        self.app_lbl.setText(
            app_metrics.elidedText(self._raw_app_line, Qt.TextElideMode.ElideRight, app_width)
        )

    def resizeEvent(self, event):
        self._fit_texts()
        super().resizeEvent(event)

    # ── Dragging ──────────────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()
