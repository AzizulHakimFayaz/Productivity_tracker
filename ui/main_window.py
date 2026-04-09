from __future__ import annotations

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget,
    QSizePolicy, QSpacerItem,
)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QPen

from styles.theme import (
    BG_MAIN, BG_SIDEBAR, BG_CARD, BG_CARD_ALT, BORDER,
    ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
)


# ─────────────────────────────────────────────────────────────────────────────
#  Logo widget  (blue circle + lightning bolt text)
# ─────────────────────────────────────────────────────────────────────────────

class _LogoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build()

    def _build(self):
        h = QHBoxLayout(self)
        h.setContentsMargins(20, 0, 20, 0)
        h.setSpacing(12)

        # Blue circle avatar with lightning emoji
        circle = QLabel("⚡")
        circle.setFixedSize(34, 34)
        circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        circle.setFont(QFont("Segoe UI", 14))
        circle.setStyleSheet(f"""
            background-color: {ACCENT};
            color: white;
            border-radius: 17px;
            font-size: 16px;
        """)
        h.addWidget(circle)

        name = QLabel("Focus.io")
        name.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        name.setStyleSheet(f"color:{TEXT_PRIMARY}; background:transparent;")
        h.addWidget(name)
        h.addStretch()


# ─────────────────────────────────────────────────────────────────────────────
#  Sidebar navigation button
# ─────────────────────────────────────────────────────────────────────────────

class _NavButton(QPushButton):
    def __init__(self, icon: str, label: str, active: bool = False, parent=None):
        super().__init__(parent)
        self._icon  = icon
        self._label = label
        self._active = active
        self.setFixedHeight(42)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setChecked(active)
        self._apply_style(active)

        # Layout inside the button
        h = QHBoxLayout(self)
        h.setContentsMargins(20, 0, 20, 0)
        h.setSpacing(12)

        ic = QLabel(icon)
        ic.setFont(QFont("Segoe UI", 14))
        ic.setFixedWidth(22)
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic.setStyleSheet("background:transparent; border:none;")
        ic.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        h.addWidget(ic)

        txt = QLabel(label)
        txt.setFont(QFont("Segoe UI", 13))
        txt.setStyleSheet("background:transparent; border:none;")
        txt.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        h.addWidget(txt)
        h.addStretch()

        self._ic  = ic
        self._txt = txt

    def _apply_style(self, active: bool):
        if active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {ACCENT}22;
                    color: {ACCENT};
                    border: none;
                    border-radius: 10px;
                    text-align: left;
                    font-weight: 700;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {TEXT_SECONDARY};
                    border: none;
                    border-radius: 10px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: {BG_CARD};
                    color: {TEXT_PRIMARY};
                }}
            """)

    def set_active(self, active: bool):
        self._active = active
        self.setChecked(active)
        self._apply_style(active)


# ─────────────────────────────────────────────────────────────────────────────
#  User info widget  (bottom of sidebar)
# ─────────────────────────────────────────────────────────────────────────────

class _UserWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(62)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build()

    def _build(self):
        h = QHBoxLayout(self)
        h.setContentsMargins(16, 0, 16, 0)
        h.setSpacing(12)

        # Avatar circle (painted)
        avatar = _AvatarCircle("A", "#5b6cf6")
        h.addWidget(avatar)

        info = QVBoxLayout()
        info.setSpacing(2)

        name = QLabel("Alex Morgan")
        name.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        name.setStyleSheet(f"color:{TEXT_PRIMARY}; background:transparent;")
        info.addWidget(name)

        plan = QLabel("Pro Plan")
        plan.setFont(QFont("Segoe UI", 10))
        plan.setStyleSheet(f"color:{TEXT_MUTED}; background:transparent;")
        info.addWidget(plan)

        h.addLayout(info)
        h.addStretch()


class _AvatarCircle(QWidget):
    def __init__(self, initials: str, color: str, size: int = 36, parent=None):
        super().__init__(parent)
        self.initials = initials
        self.color    = QColor(color)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(self.color))
        p.drawEllipse(0, 0, self.width(), self.height())
        p.setPen(QColor("white"))
        p.setFont(QFont("Segoe UI", int(self.width() * 0.38), QFont.Weight.Bold))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.initials)
        p.end()


# ─────────────────────────────────────────────────────────────────────────────
#  Sidebar
# ─────────────────────────────────────────────────────────────────────────────

class Sidebar(QFrame):
    """
    Left-side navigation panel.
    Emits page-change signals via the `on_page_change` callback.
    """

    on_page_change = None   # callable(index: int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(230)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_SIDEBAR};
                border-right: 1px solid {BORDER};
                border-radius: 0px;
            }}
        """)

        self._nav_buttons: list[_NavButton] = []
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(10, 0, 10, 0)
        v.setSpacing(0)

        # Logo
        v.addSpacing(10)
        v.addWidget(_LogoWidget())
        v.addSpacing(24)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{BORDER}; border:none;")
        v.addWidget(sep)
        v.addSpacing(16)

        # Nav items
        nav_items = [
            ("⊞", "Dashboard"),
            ("≡", "Analytics"),
            ("□", "Planner"),
            ("◎", "Sessions"),
            ("⚙", "Settings"),
            ("⚗", "AI Debug"),
        ]

        for i, (icon, label) in enumerate(nav_items):
            btn = _NavButton(icon, label, active=(i == 0))
            btn.clicked.connect(lambda checked, idx=i: self._switch(idx))
            self._nav_buttons.append(btn)
            v.addWidget(btn)
            v.addSpacing(4)

        v.addStretch()

        # Bottom separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setFixedHeight(1)
        sep2.setStyleSheet(f"background:{BORDER}; border:none;")
        v.addWidget(sep2)

        # User info
        v.addWidget(_UserWidget())

    def _switch(self, index: int):
        for i, btn in enumerate(self._nav_buttons):
            btn.set_active(i == index)
        if callable(self.on_page_change):
            self.on_page_change(index)

    def set_active_index(self, index: int):
        self._switch(index)

    def toggle_sidebar(self):
        width = self.width()
        if width == 230:
            new_width = 0
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {BG_SIDEBAR};
                    border-right: none;
                    border-radius: 0px;
                }}
            """)
        else:
            new_width = 230
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {BG_SIDEBAR};
                    border-right: 1px solid {BORDER};
                    border-radius: 0px;
                }}
            """)

        self.animation = QPropertyAnimation(self, b"maximumWidth")
        self.animation.setDuration(300)
        self.animation.setStartValue(width)
        self.animation.setEndValue(new_width)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuart)

        self.animation2 = QPropertyAnimation(self, b"minimumWidth")
        self.animation2.setDuration(300)
        self.animation2.setStartValue(width)
        self.animation2.setEndValue(new_width)
        self.animation2.setEasingCurve(QEasingCurve.Type.InOutQuart)

        self.animation.start()
        self.animation2.start()


# ─────────────────────────────────────────────────────────────────────────────
#  Main Window
# ─────────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Focus.io")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 860)
        self.setStyleSheet(f"background-color:{BG_MAIN};")

        # Central container
        central = QWidget()
        central.setStyleSheet(f"background-color:{BG_MAIN};")
        self.setCentralWidget(central)

        main_h = QHBoxLayout(central)
        main_h.setContentsMargins(0, 0, 0, 0)
        main_h.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        self._sidebar = Sidebar()
        self._sidebar.on_page_change = self._on_nav_change
        main_h.addWidget(self._sidebar)

        # ── Stacked page area ─────────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background-color:{BG_MAIN};")
        main_h.addWidget(self._stack, stretch=1)

        self._load_pages()
        self._stack.setCurrentIndex(0)
        self._engine = None

    # ── page loading (lazy-ish) ───────────────────────────────────────────────
    def _load_pages(self):
        from ui.dashboard_page import DashboardPage
        from ui.analytics_page import AnalyticsPage
        from ui.planner_page import PlannerPage
        from ui.settings_page import SettingsPage
        from ui.ai_debug_page import AIDebugPage

        self._dash_page  = DashboardPage()
        self._analytics  = AnalyticsPage()
        self._planner = PlannerPage()

        # Sessions placeholder
        self._sessions_ph = _PlaceholderPage("Sessions", "◎", "Review all your focus sessions.")
        self._settings = SettingsPage()
        self._ai_debug = AIDebugPage()

        for page in [
            self._dash_page,
            self._analytics,
            self._planner,
            self._sessions_ph,
            self._settings,
            self._ai_debug,
        ]:
            self._stack.addWidget(page)

    def _on_nav_change(self, index: int):
        self._stack.setCurrentIndex(index)
        if index == 2 and hasattr(self, "_planner"):
            self._planner.refresh_tasks()

    def set_engine(self, engine):
        self._engine = engine
        if hasattr(self, "_settings") and self._settings:
            self._settings.set_engine(engine)
        if hasattr(self, "_planner") and self._planner:
            self._planner.set_engine(engine)

    def closeEvent(self, event):
        """Hide to system tray — keep tracking in the background."""
        from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
        event.ignore()   # Don't actually close
        self.hide()      # Just hide the window
        # Show a tray balloon so the user knows it's still running
        app_instance = QApplication.instance()
        if hasattr(app_instance, 'tray') and app_instance.tray:
            app_instance.tray.showMessage(
                "Focus.io is still running",
                "Tracking in the background. Right-click the tray icon to quit.",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )


# ─────────────────────────────────────────────────────────────────────────────
#  Placeholder pages for Projects / Sessions
# ─────────────────────────────────────────────────────────────────────────────

class _PlaceholderPage(QWidget):
    def __init__(self, title: str, icon: str, subtitle: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color:{BG_MAIN};")

        v = QVBoxLayout(self)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.setSpacing(16)

        ic = QLabel(icon)
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic.setFont(QFont("Segoe UI", 52))
        ic.setStyleSheet(f"color:{BORDER}; background:transparent;")
        v.addWidget(ic)

        ttl = QLabel(title)
        ttl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ttl.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        ttl.setStyleSheet(f"color:{TEXT_SECONDARY}; background:transparent;")
        v.addWidget(ttl)

        sub = QLabel(subtitle)
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setFont(QFont("Segoe UI", 13))
        sub.setStyleSheet(f"color:{TEXT_MUTED}; background:transparent;")
        v.addWidget(sub)

        soon = QLabel("Coming soon")
        soon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        soon.setFont(QFont("Segoe UI", 11))
        soon.setStyleSheet(f"""
            color: {ACCENT};
            background-color: {ACCENT}22;
            border: 1px solid {ACCENT}55;
            border-radius: 8px;
            padding: 6px 20px;
        """)
        v.addWidget(soon, alignment=Qt.AlignmentFlag.AlignCenter)
