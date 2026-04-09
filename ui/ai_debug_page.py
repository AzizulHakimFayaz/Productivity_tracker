from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QFrame
)

from styles.theme import BG_MAIN, BG_CARD, BORDER, TEXT_PRIMARY, TEXT_MUTED, ACCENT
from backend.ai_debug import get_ai_debug_logs, clear_ai_debug_logs, get_model_status


class AIDebugPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG_MAIN};")
        self._last_line = ""
        self._build()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(1000)
        self._refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("AI Debug (Temporary)")
        title.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{TEXT_PRIMARY}; background:transparent; border:none;")
        root.addWidget(title)

        sub = QLabel("Live classifier diagnostics: model state + Rule/AI decisions.")
        sub.setStyleSheet(f"color:{TEXT_MUTED}; background:transparent; border:none;")
        root.addWidget(sub)

        top = QFrame()
        top.setStyleSheet(f"background:{BG_CARD}; border:1px solid {BORDER}; border-radius:12px;")
        top_l = QHBoxLayout(top)
        top_l.setContentsMargins(14, 10, 14, 10)
        top_l.setSpacing(12)

        self._status = QLabel("Model: loading")
        self._status.setStyleSheet("border:none; background:transparent; color:#dbe4ff; font-weight:700;")
        top_l.addWidget(self._status)
        top_l.addStretch()

        self._btn_clear = QPushButton("Clear Logs")
        self._btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_clear.setStyleSheet(
            f"QPushButton{{background:{ACCENT}22; color:{ACCENT}; border:1px solid {ACCENT}66; border-radius:8px; padding:6px 12px;}}"
            f"QPushButton:hover{{background:{ACCENT}33;}}"
        )
        self._btn_clear.clicked.connect(self._on_clear)
        top_l.addWidget(self._btn_clear)
        root.addWidget(top)

        self._log_box = QTextEdit()
        self._log_box.setReadOnly(True)
        self._log_box.setStyleSheet(
            f"QTextEdit{{background:{BG_CARD}; color:{TEXT_PRIMARY}; border:1px solid {BORDER}; border-radius:12px; padding:10px;}}"
        )
        self._log_box.setFont(QFont("Consolas", 10))
        root.addWidget(self._log_box, 1)

    def _on_clear(self):
        clear_ai_debug_logs()
        self._log_box.clear()
        self._last_line = ""

    def _refresh(self):
        status = get_model_status()
        self._status.setText(f"Model: {status}")
        lines = get_ai_debug_logs(500)
        if not lines:
            self._log_box.setPlainText("No logs yet. Start tracking activity to see Rule/AI detection logs.")
            return
        if lines[-1] != self._last_line:
            self._log_box.setPlainText("\n".join(lines))
            self._log_box.verticalScrollBar().setValue(self._log_box.verticalScrollBar().maximum())
            self._last_line = lines[-1]
