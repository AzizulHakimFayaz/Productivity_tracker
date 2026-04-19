from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from styles.theme import ACCENT, BG_CARD, BG_CARD_ALT, BORDER, CYAN, GREEN, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY


class BreakReminderDialog(QDialog):
    def __init__(
        self,
        title: str,
        message: str,
        confirm_text: str = "Take Break",
        snooze_text: str = "Snooze 10m",
        parent=None,
    ):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self._title = title
        self._message = message
        self._confirm_text = confirm_text
        self._snooze_text = snooze_text
        self.on_confirm = None
        self.on_snooze = None
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("breakCard")
        card.setStyleSheet(
            f"""
            QFrame#breakCard {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 22px;
            }}
            """
        )
        root.addWidget(card)

        inner = QVBoxLayout(card)
        inner.setContentsMargins(26, 24, 26, 22)
        inner.setSpacing(0)

        badge = QLabel("RECOVERY")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedWidth(104)
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
        inner.addWidget(badge, alignment=Qt.AlignmentFlag.AlignLeft)

        inner.addSpacing(16)

        title = QLabel(self._title)
        title.setWordWrap(True)
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{TEXT_PRIMARY}; background:transparent;")
        inner.addWidget(title)

        inner.addSpacing(10)

        message = QLabel(self._message)
        message.setWordWrap(True)
        message.setFont(QFont("Segoe UI", 11))
        message.setStyleSheet(f"color:{TEXT_SECONDARY}; background:transparent; line-height:1.35;")
        inner.addWidget(message)

        inner.addSpacing(20)

        hint = QLabel("Short resets protect energy and keep the next sprint sharp.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{TEXT_MUTED}; background:transparent;")
        inner.addWidget(hint)

        inner.addSpacing(22)

        buttons = QHBoxLayout()
        buttons.setSpacing(12)

        snooze = QPushButton(self._snooze_text)
        snooze.setCursor(Qt.CursorShape.PointingHandCursor)
        snooze.setFixedHeight(42)
        snooze.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {BG_CARD_ALT};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER};
                border-radius: 12px;
                padding: 0 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #445066;
            }}
            """
        )
        snooze.clicked.connect(self._handle_snooze)
        buttons.addWidget(snooze)

        confirm = QPushButton(self._confirm_text)
        confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm.setFixedHeight(42)
        confirm.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {ACCENT};
                color: white;
                border: none;
                border-radius: 12px;
                padding: 0 18px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: #4f46e5;
            }}
            """
        )
        confirm.clicked.connect(self._handle_confirm)
        buttons.addWidget(confirm)

        inner.addLayout(buttons)
        self.setFixedSize(440, 250)

    def showEvent(self, event):
        super().showEvent(event)
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + max(40, (geo.height() - self.height()) // 3)
            self.move(x, y)
        self.raise_()
        self.activateWindow()

    def _handle_confirm(self):
        if callable(self.on_confirm):
            self.on_confirm()
        self.accept()

    def _handle_snooze(self):
        if callable(self.on_snooze):
            self.on_snooze()
        self.accept()


def show_break_dialog(
    title: str,
    message: str,
    confirm_text: str = "Take Break",
    snooze_text: str = "Snooze 10m",
    on_confirm=None,
    on_snooze=None,
) -> BreakReminderDialog:
    dlg = BreakReminderDialog(
        title=title,
        message=message,
        confirm_text=confirm_text,
        snooze_text=snooze_text,
    )
    dlg.on_confirm = on_confirm
    dlg.on_snooze = on_snooze
    return dlg
