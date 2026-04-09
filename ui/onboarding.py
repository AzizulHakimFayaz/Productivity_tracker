from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QFrame, QMainWindow,
    QSizePolicy, QSpacerItem,
)
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint, QSize
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush,
    QPainterPath, QLinearGradient,
)

from styles.theme import (
    BG_MAIN, BG_CARD, BG_CARD_ALT, BORDER,
    ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, GREEN,
)
from ui.ui_effects import apply_soft_shadow


# ─── helpers ─────────────────────────────────────────────────────────────────

def _lbl(text: str, size: int = 13, bold: bool = False,
         color: str = TEXT_PRIMARY, align=Qt.AlignmentFlag.AlignLeft) -> QLabel:
    l = QLabel(text)
    w = QFont.Weight.Bold if bold else QFont.Weight.Normal
    l.setFont(QFont("Segoe UI", size, w))
    l.setStyleSheet(f"color: {color}; background: transparent; border: none;")
    l.setAlignment(align)
    return l


# ─────────────────────────────────────────────────────────────────────────────
#  Welcome Screen  (Step 1 – grid background)
# ─────────────────────────────────────────────────────────────────────────────

class _ClockIcon(QWidget):
    """Custom-painted clock icon matching the design."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 120)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx, cy, r = 60, 60, 44

        # outer dashed circle
        pen = QPen(QColor(ACCENT))
        pen.setWidth(2)
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setDashPattern([4, 3])
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # inner solid circle
        inner_r = 34
        pen.setStyle(Qt.PenStyle.SolidLine)
        pen.setColor(QColor(ACCENT))
        painter.setPen(pen)
        painter.drawEllipse(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)

        # clock hands
        pen2 = QPen(QColor(ACCENT), 2, Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap)
        painter.setPen(pen2)
        # minute hand (pointing ~to 12)
        painter.drawLine(cx, cy, cx, cy - 22)
        # hour hand (pointing ~to 9)
        painter.drawLine(cx, cy, cx - 16, cy)

        # center dot
        painter.setBrush(QColor(ACCENT))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx - 4, cy - 4, 8, 8)

        # accent arc on top-right
        arc_pen = QPen(QColor(ACCENT), 3)
        arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(arc_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        margin = 8
        arc_rect = QRect(margin, margin,
                         self.width() - margin * 2,
                         self.height() - margin * 2)
        painter.drawArc(arc_rect, 30 * 16, 60 * 16)

        painter.end()


class WelcomeScreen(QWidget):
    """
    Onboarding Page 1 – dark background with a subtle grid, clock icon,
    hero text, 'Start Setup' button and dot/step indicators.
    """

    on_start = None          # callback assigned by OnboardingWindow

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    # ── grid background ───────────────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#0d1117"))

        grid_pen = QPen(QColor("#1c2a3a"), 1)
        painter.setPen(grid_pen)
        step = 38
        for x in range(0, self.width() + step, step):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height() + step, step):
            painter.drawLine(0, y, self.width(), y)

        painter.end()

    # ── layout ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 40)
        root.setSpacing(0)

        root.addStretch(3)

        # clock
        clock_row = QHBoxLayout()
        clock_row.addStretch()
        clock_row.addWidget(_ClockIcon())
        clock_row.addStretch()
        root.addLayout(clock_row)

        root.addSpacing(36)

        # hero title  "Welcome to Your 168-Hour Tracker"
        title_row = QHBoxLayout()
        title_row.addStretch()

        title_lbl = QLabel()
        title_lbl.setTextFormat(Qt.TextFormat.RichText)
        title_lbl.setText(
            f'<span style="color:{TEXT_PRIMARY};font-size:32px;font-weight:800;">'
            f'Welcome to Your </span>'
            f'<span style="color:{ACCENT};font-size:32px;font-weight:800;">'
            f'168-<br>Hour</span>'
            f'<span style="color:{TEXT_PRIMARY};font-size:32px;font-weight:800;">'
            f' Tracker</span>'
        )
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title_lbl.setStyleSheet("background: transparent;")
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        root.addLayout(title_row)

        root.addSpacing(18)

        # subtitle
        sub = _lbl(
            "Master your week. Track your focus, analyze your habits,\n"
            "and reclaim your time with precision analytics.",
            size=12, color=TEXT_SECONDARY,
            align=Qt.AlignmentFlag.AlignHCenter,
        )
        sub.setStyleSheet(f"color:{TEXT_SECONDARY}; background:transparent;")
        sub.setWordWrap(True)
        root.addWidget(sub)

        root.addSpacing(38)

        # Start Setup button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn = _StartButton("Start Setup  →")
        btn.clicked.connect(self._on_start_clicked)
        btn_row.addWidget(btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        root.addSpacing(30)

        # dot indicators  ● ○ ○ ○ ○
        dots_row = QHBoxLayout()
        dots_row.addStretch()
        for i in range(5):
            d = QLabel("●" if i == 0 else "●")
            d.setStyleSheet(
                f"color: {ACCENT}; font-size: 10px; background: transparent;"
                if i == 0 else
                f"color: #30363d; font-size: 10px; background: transparent;"
            )
            dots_row.addWidget(d)
            if i < 4:
                dots_row.addSpacing(6)
        dots_row.addStretch()
        root.addLayout(dots_row)

        root.addSpacing(8)

        step_lbl = _lbl("STEP 1 OF 5", 9, color=TEXT_MUTED,
                         align=Qt.AlignmentFlag.AlignHCenter)
        step_lbl.setStyleSheet(
            f"color:{TEXT_MUTED}; letter-spacing:2px; background:transparent;")
        root.addWidget(step_lbl)

        root.addStretch(1)

        # copyright
        copy = _lbl("© 2023 Chronos Analytics. All rights reserved.",
                     9, color=TEXT_MUTED,
                     align=Qt.AlignmentFlag.AlignHCenter)
        copy.setStyleSheet(f"color:{TEXT_MUTED}; background:transparent;")
        root.addWidget(copy)

    def _on_start_clicked(self):
        if callable(self.on_start):
            self.on_start()


# ─────────────────────────────────────────────────────────────────────────────
#  Category Selection Step  (Step 2 – "What brings you here?")
# ─────────────────────────────────────────────────────────────────────────────

class _CategoryCard(QFrame):
    """Single selectable category card."""

    def __init__(self, icon: str, title: str, description: str, parent=None):
        super().__init__(parent)
        self.icon_text = icon
        self._selected = False
        self.setFixedSize(210, 210)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style()
        self._build_ui(icon, title, description)
        apply_soft_shadow(self, blur_radius=26, offset_y=6, alpha=66)

    # ── style helpers ─────────────────────────────────────────────────────────
    def _apply_style(self):
        if self._selected:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {BG_CARD};
                    border: 2px solid {ACCENT};
                    border-radius: 14px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {BG_CARD};
                    border: 1px solid {BORDER};
                    border-radius: 14px;
                }}
                QFrame:hover {{
                    border: 1px solid #4d5566;
                }}
            """)

    def set_selected(self, selected: bool):
        self._selected = selected
        self._apply_style()
        self.update()

    @property
    def selected(self) -> bool:
        return self._selected

    def mousePressEvent(self, event):
        self.set_selected(not self._selected)
        super().mousePressEvent(event)

    # ── layout ────────────────────────────────────────────────────────────────
    def _build_ui(self, icon: str, title: str, description: str):
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 18, 18, 18)
        v.setSpacing(0)

        # icon badge
        icon_frame = QFrame()
        icon_frame.setFixedSize(48, 48)
        icon_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {ACCENT};
                border-radius: 12px;
                border: none;
            }}
        """)
        icon_layout = QHBoxLayout(icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            "color: white; font-size: 20px; background: transparent; border: none;")
        icon_layout.addWidget(icon_lbl)

        top_row = QHBoxLayout()
        top_row.addWidget(icon_frame)
        top_row.addStretch()

        # checkmark (visible only when selected)
        self._check = QLabel("✓")
        self._check.setFixedSize(22, 22)
        self._check.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._check.setStyleSheet(f"""
            color: white;
            background-color: {ACCENT};
            border-radius: 11px;
            font-size: 12px;
            font-weight: bold;
            border: none;
        """)
        self._check.setVisible(False)
        top_row.addWidget(self._check)

        v.addLayout(top_row)
        v.addSpacing(18)

        # title
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet(
            f"color:{TEXT_PRIMARY}; background:transparent; border:none;")
        v.addWidget(title_lbl)

        v.addSpacing(10)

        # description
        desc_lbl = QLabel(description)
        desc_lbl.setFont(QFont("Segoe UI", 11))
        desc_lbl.setStyleSheet(
            f"color:{TEXT_SECONDARY}; background:transparent; border:none;")
        desc_lbl.setWordWrap(True)
        v.addWidget(desc_lbl)
        v.addStretch()

    def set_selected(self, selected: bool):
        self._selected = selected
        self._apply_style()
        # show/hide check
        check = self.findChild(QLabel, "")
        for child in self.findChildren(QLabel):
            if child.text() == "✓":
                child.setVisible(selected)
        self.update()


class CategoryStep(QWidget):
    """
    Onboarding Page 2 – 'What brings you here?' with 4 selectable cards,
    step progress dashes, Go Back and Continue buttons.
    """

    on_back     = None   # callbacks
    on_continue = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {BG_MAIN};")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(60, 60, 60, 60)
        root.setSpacing(0)

        root.addStretch(2)

        # ── step dashes ───────────────────────────────────────────────────────
        dash_row = QHBoxLayout()
        dash_row.setSpacing(6)
        dash_row.addStretch()
        step_label_row = QHBoxLayout()
        step_label_row.setSpacing(6)
        step_label_row.addStretch()

        for i in range(4):
            dash = QFrame()
            dash.setFixedSize(50, 4)
            if i < 2:
                dash.setStyleSheet(
                    f"background:{ACCENT}; border-radius:2px;")
            else:
                dash.setStyleSheet(
                    "background:#2d3748; border-radius:2px;")
            dash_row.addWidget(dash)

        step_txt = _lbl("Step 2 of 4", 11, color=TEXT_SECONDARY)
        step_txt.setStyleSheet(
            f"color:{TEXT_SECONDARY}; background:transparent; margin-left:10px;")
        dash_row.addWidget(step_txt)
        dash_row.addStretch()
        root.addLayout(dash_row)

        root.addSpacing(40)

        # ── heading ───────────────────────────────────────────────────────────
        heading = _lbl("What brings you here?", 28, bold=True,
                        align=Qt.AlignmentFlag.AlignHCenter)
        heading.setStyleSheet(
            f"color:{TEXT_PRIMARY}; font-weight:800; background:transparent;")
        root.addWidget(heading)

        root.addSpacing(14)

        subtitle = _lbl(
            "Select the main activity you want to track to get personalized analytics and focus insights.",
            13, color=TEXT_SECONDARY,
            align=Qt.AlignmentFlag.AlignHCenter,
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            f"color:{TEXT_SECONDARY}; background:transparent;")
        root.addWidget(subtitle)

        root.addSpacing(44)

        # ── 4 category cards ──────────────────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        cards_row.addStretch()

        self._cards: list[_CategoryCard] = []
        categories = [
            ("⟨/⟩", "Development",
             "Code tracking, GitHub integration, and deep work sessions for engineering."),
            ("🎓", "Study",
             "Academic focus timers, research organization, and retention analytics."),
            ("💼", "Freelancing",
             "Billable hours tracking, project separation, and client reporting tools."),
            ("⚙", "Custom",
             "Define your own path. Configure specific tags and focus categories manually."),
        ]

        for icon, title, desc in categories:
            card = _CategoryCard(icon, title, desc)
            self._cards.append(card)
            cards_row.addWidget(card)

        # Select first card by default
        self._cards[0].set_selected(True)

        cards_row.addStretch()
        root.addLayout(cards_row)

        root.addStretch(2)

        # ── bottom navigation ─────────────────────────────────────────────────
        nav_row = QHBoxLayout()

        back_btn = QPushButton("Go Back")
        back_btn.setFont(QFont("Segoe UI", 12))
        back_btn.setStyleSheet(f"""
            QPushButton {{
                color: {TEXT_SECONDARY};
                background: transparent;
                border: none;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                color: {TEXT_PRIMARY};
            }}
        """)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(lambda: self.on_back and self.on_back())

        nav_row.addWidget(back_btn)
        nav_row.addStretch()

        continue_btn = _StartButton("Continue  →")
        continue_btn.clicked.connect(self._handle_continue)
        nav_row.addWidget(continue_btn)

        root.addLayout(nav_row)

    def _handle_continue(self):
        if callable(self.on_continue):
            self.on_continue()


# ─────────────────────────────────────────────────────────────────────────────
#  Shared styled button
# ─────────────────────────────────────────────────────────────────────────────

class _StartButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFixedSize(200, 50)
        self.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT};
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #2563eb;
            }}
            QPushButton:pressed {{
                background-color: #1d4ed8;
            }}
        """)


# ─────────────────────────────────────────────────────────────────────────────
#  Onboarding Window  (orchestrates all steps)
# ─────────────────────────────────────────────────────────────────────────────

class OnboardingWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Focus.io – Setup")
        self.setMinimumSize(900, 680)
        self.resize(1100, 750)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        # Page 0 – welcome
        self._welcome = WelcomeScreen()
        self._welcome.on_start = lambda: self._stack.setCurrentIndex(1)
        self._stack.addWidget(self._welcome)

        # Page 1 – category
        self._cat = CategoryStep()
        self._cat.on_back     = lambda: self._stack.setCurrentIndex(0)
        self._cat.on_continue = self._finish_onboarding
        self._stack.addWidget(self._cat)

        self._stack.setCurrentIndex(0)

    def _finish_onboarding(self):
        """Launch the main application window."""
        from ui.main_window import MainWindow
        self._main = MainWindow()
        self._main.show()
        self.close()
