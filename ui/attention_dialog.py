from __future__ import annotations

from PyQt6.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGraphicsOpacityEffect,
)
from PyQt6.QtCore import Qt, QSize, QRect, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QBrush, QPen,
    QPainterPath, QLinearGradient,
)

from styles.theme import (
    BG_CARD, BG_CARD_ALT, BORDER,
    ACCENT_PURPLE, ACCENT_PURPLE_DARK,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    BG_MAIN, DANGER,
)

# ─────────────────────────────────────────────────────────────────────────────
#  Warning icon  (amber circle + ⚠ triangle painted)
# ─────────────────────────────────────────────────────────────────────────────

class _WarningIcon(QWidget):
    """Painted amber circle containing a white warning triangle."""

    def __init__(self, size: int = 56, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Outer amber ring
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#78350f")))
        p.drawEllipse(0, 0, self._size, self._size)

        # Inner amber circle
        p.setBrush(QBrush(QColor("#b45309")))
        margin = int(self._size * 0.08)
        p.drawEllipse(margin, margin,
                      self._size - margin * 2,
                      self._size - margin * 2)

        # Warning text
        p.setPen(QColor("#fbbf24"))
        font = QFont("Segoe UI", int(self._size * 0.38), QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(QRect(0, 0, self._size, self._size),
                   Qt.AlignmentFlag.AlignCenter, "⚠")
        p.end()


# ─────────────────────────────────────────────────────────────────────────────
#  Snooze button  (outlined dark)
# ─────────────────────────────────────────────────────────────────────────────

class _SnoozeButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__("  Snooze", parent)
        self.setFixedHeight(48)
        self.setMinimumWidth(160)
        self.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style(False)

    def _apply_style(self, hover: bool):
        bg = "#2a3244" if hover else "#1e2736"
        self.setStyleSheet(f"""
            QPushButton {{
                color: {TEXT_PRIMARY};
                background-color: {bg};
                border: 1.5px solid {BORDER};
                border-radius: 24px;
                padding: 0 24px;
                font-size: 13px;
                font-weight: 600;
                text-align: center;
            }}
        """)

    def enterEvent(self, event):
        self._apply_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style(False)
        super().leaveEvent(event)


# ─────────────────────────────────────────────────────────────────────────────
#  Resume Task button  (solid purple)
# ─────────────────────────────────────────────────────────────────────────────

class _ResumeButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__("  Focus Now", parent)
        self.setFixedHeight(48)
        self.setMinimumWidth(180)
        self.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style(False)

    def _apply_style(self, hover: bool):
        bg = ACCENT_PURPLE_DARK if hover else ACCENT_PURPLE
        self.setStyleSheet(f"""
            QPushButton {{
                color: white;
                background-color: {bg};
                border: none;
                border-radius: 24px;
                padding: 0 24px;
                font-size: 13px;
                font-weight: 600;
                text-align: center;
            }}
        """)

    def enterEvent(self, event):
        self._apply_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style(False)
        super().leaveEvent(event)


# ─────────────────────────────────────────────────────────────────────────────
#  The dialog card  (painted rounded rectangle)
# ─────────────────────────────────────────────────────────────────────────────

class _DialogCard(QFrame):
    """The visible dark card in the centre of the overlay."""

    def __init__(
        self,
        task_name: str = "Productivity Alert",
        warning_message: str = (
            "You've been spending a lot of time on non-productive activities. "
            "Consider refocusing on your work."
        ),
        parent=None,
    ):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(460)
        self._task_name = task_name
        self._warning_message = warning_message
        self._build()

    # ── layout ────────────────────────────────────────────────────────────────
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(44, 38, 44, 30)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # ── Warning icon ─────────────────────────────────────────────────────
        icon_row = QHBoxLayout()
        icon_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        icon_row.addWidget(_WarningIcon(60))
        root.addLayout(icon_row)

        root.addSpacing(20)

        # ── Title ─────────────────────────────────────────────────────────────
        title = QLabel("Attention Needed")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{TEXT_PRIMARY}; background:transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        root.addSpacing(8)

        # ── Sub-title: task name ───────────────────────────────────────────────
        task_lbl = QLabel(self._task_name)
        task_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        task_lbl.setStyleSheet(f"""
            color: #fbbf24;
            background-color: #78350f44;
            border: 1px solid #b4530966;
            border-radius: 8px;
            padding: 4px 14px;
        """)
        task_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(task_lbl, alignment=Qt.AlignmentFlag.AlignHCenter)

        root.addSpacing(18)

        # ── Message ─────────────────────────────────────────────────────────
        msg = QLabel(self._warning_message)
        msg.setFont(QFont("Segoe UI", 11))
        msg.setStyleSheet(f"color:{TEXT_SECONDARY}; background:transparent;")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setWordWrap(True)
        root.addWidget(msg)

        root.addSpacing(24)

        # ── Divider ──────────────────────────────────────────────────────────
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet(f"background:{BORDER}; border:none;")
        root.addWidget(div)

        root.addSpacing(20)

        # ── Buttons ──────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        snooze_btn = _SnoozeButton()
        snooze_btn.setText("🕐  Snooze 10m")
        snooze_btn.clicked.connect(self._on_snooze)
        btn_row.addWidget(snooze_btn)

        resume_btn = _ResumeButton()
        resume_btn.setText("⚡  Focus Now")
        resume_btn.clicked.connect(self._on_resume)
        btn_row.addWidget(resume_btn)

        root.addLayout(btn_row)

        root.addSpacing(16)

        # ── Footer ───────────────────────────────────────────────────────────
        footer = QLabel("Focus.io monitors your activity to help you stay on track.")
        footer.setFont(QFont("Segoe UI", 10))
        footer.setStyleSheet(f"color:{TEXT_MUTED}; background:transparent;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(footer)

    # ── button callbacks ──────────────────────────────────────────────────────
    def _on_snooze(self):
        if callable(getattr(self, "on_snooze", None)):
            self.on_snooze()

    def _on_resume(self):
        if callable(getattr(self, "on_resume", None)):
            self.on_resume()

    # ── paint the rounded rectangle background ────────────────────────────────
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 20, 20)

        # Card fill with subtle gradient
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#1e2a3f"))
        grad.setColorAt(1.0, QColor("#16202f"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(path)

        # Accent top highlight
        highlight_path = QPainterPath()
        highlight_path.addRoundedRect(0, 0, self.width(), 3, 2, 2)
        p.setBrush(QBrush(QColor("#b45309")))
        p.drawPath(highlight_path)

        # Card border
        p.setPen(QPen(QColor("#2d3748"), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        p.end()


# ─────────────────────────────────────────────────────────────────────────────
#  Full-screen overlay dialog
# ─────────────────────────────────────────────────────────────────────────────

class AttentionNeededDialog(QDialog):
    """
    Full-screen system overlay that floats above ALL windows (like Rize).

    Usage
    -----
    dlg = AttentionNeededDialog(
        task_name       = "Entertainment Alert",
        warning_message = "You've been on YouTube for 5 minutes.",
    )
    dlg.on_snooze = lambda: ...
    dlg.on_resume = lambda: ...
    dlg.exec()
    """

    def __init__(
        self,
        parent=None,
        task_name: str = "Productivity Alert",
        warning_message: str = (
            "You've been spending a lot of time on non-productive activities."
        ),
    ):
        # FramelessWindowHint + WindowStaysOnTopHint = floats above everything
        super().__init__(
            None,   # No parent — must be top-level to cover all windows
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)

        self._task_name = task_name
        self._warning_message = warning_message

        # Callbacks (set by caller)
        self.on_snooze: callable | None = None
        self.on_resume: callable | None = None

        self._build()

        # Cover the entire primary screen
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

    # ── layout ────────────────────────────────────────────────────────────────
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._card = _DialogCard(
            task_name=self._task_name,
            warning_message=self._warning_message,
        )
        self._card.on_snooze = self._handle_snooze
        self._card.on_resume = self._handle_resume
        root.addWidget(self._card, alignment=Qt.AlignmentFlag.AlignCenter)

    # ── always fill the full screen ───────────────────────────────────────────
    def showEvent(self, event):
        super().showEvent(event)
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())
        self.raise_()
        self.activateWindow()

    # ── paint semi-transparent dark overlay across full screen ─────────────────
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor(0, 0, 0, 190)))   # ~75% opaque black
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(self.rect())
        p.end()

    # ── button handlers ───────────────────────────────────────────────────────
    def _handle_snooze(self):
        if callable(self.on_snooze):
            self.on_snooze()
        self.accept()

    def _handle_resume(self):
        if callable(self.on_resume):
            self.on_resume()
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
#  Convenience launcher
# ─────────────────────────────────────────────────────────────────────────────

def show_attention_dialog(
    parent=None,
    task_name: str = "Productivity Alert",
    warning_message: str = (
        "You've been spending a lot of time on non-productive activities. "
        "Consider refocusing on your work."
    ),
    on_snooze=None,
    on_resume=None,
) -> AttentionNeededDialog:
    """
    Create and wire up a full-screen system-level AttentionNeededDialog.
    The parent argument is ignored — the overlay always covers the full screen.

    Example
    -------
    dlg = show_attention_dialog(
        task_name       = "Entertainment Alert",
        warning_message = "You've been watching videos for 5 minutes.",
        on_snooze       = lambda: print("snoozed"),
        on_resume       = lambda: print("resuming"),
    )
    dlg.exec()
    """
    dlg = AttentionNeededDialog(None, task_name, warning_message)
    if on_snooze:
        dlg.on_snooze = on_snooze
    if on_resume:
        dlg.on_resume = on_resume
    return dlg
