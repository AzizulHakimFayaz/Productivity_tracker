from __future__ import annotations

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget,
    QSizePolicy, QSpacerItem,
)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QPen, QLinearGradient

from styles.theme import (
    BG_MAIN, BG_SIDEBAR, BG_CARD, BG_CARD_ALT, BORDER, BORDER_LIGHT,
    ACCENT, ACCENT_GLOW, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
)


# ─────────────────────────────────────────────────────────────────────────────
#  Logo widget  — gradient pill with lightning bolt
# ─────────────────────────────────────────────────────────────────────────────

class _LogoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(64)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build()

    def _build(self):
        h = QHBoxLayout(self)
        h.setContentsMargins(18, 0, 18, 0)
        h.setSpacing(12)

        # Gradient circle avatar
        circle = _GradientCircle()
        h.addWidget(circle)

        col = QVBoxLayout()
        col.setSpacing(1)

        name = QLabel("Focus.io")
        name.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        name.setStyleSheet(f"color:{TEXT_PRIMARY}; background:transparent;")
        col.addWidget(name)

        tagline = QLabel("Stay in your zone")
        tagline.setFont(QFont("Segoe UI", 9))
        tagline.setStyleSheet(f"color:{TEXT_MUTED}; background:transparent;")
        col.addWidget(tagline)

        h.addLayout(col)
        h.addStretch()


class _GradientCircle(QWidget):
    """A small circle with indigo→purple gradient and a ⚡ in the centre."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(38, 38)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Gradient fill
        grad = QLinearGradient(0, 0, 38, 38)
        grad.setColorAt(0.0, QColor("#6366f1"))
        grad.setColorAt(1.0, QColor("#a855f7"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(0, 0, 38, 38)

        # Lightning text
        p.setPen(QColor("white"))
        p.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "⚡")
        p.end()


# ─────────────────────────────────────────────────────────────────────────────
#  Sidebar navigation button — modern with left accent bar
# ─────────────────────────────────────────────────────────────────────────────

class _NavButton(QPushButton):
    NAV_ITEMS = [
        ("🏠", "Dashboard"),
        ("📊", "Analytics"),
        ("📅", "Planner"),
        ("⚡", "Focus Mode"),
        ("⚙", "Settings"),
        ("🧬", "AI Debug"),
    ]

    def __init__(self, icon: str, label: str, active: bool = False, parent=None):
        super().__init__(parent)
        self._icon  = icon
        self._label = label
        self._active = active
        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setChecked(active)
        self._apply_style(active)

        # Layout inside the button
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 16, 0)
        h.setSpacing(0)

        # Left accent bar
        self._accent_bar = QFrame()
        self._accent_bar.setFixedWidth(3)
        self._accent_bar.setFixedHeight(24)
        self._accent_bar.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #6366f1, stop:1 #a855f7);"
            f"border-radius: 2px; border:none;"
        )
        self._accent_bar.setVisible(active)
        h.addWidget(self._accent_bar)
        h.addSpacing(13)

        ic = QLabel(icon)
        ic.setFont(QFont("Segoe UI", 15))
        ic.setFixedWidth(24)
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic.setStyleSheet("background:transparent; border:none;")
        ic.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        h.addWidget(ic)

        h.addSpacing(12)

        txt = QLabel(label)
        txt.setFont(QFont("Segoe UI", 12))
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
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6366f120, stop:1 transparent);
                    color: {ACCENT_GLOW};
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
                    padding-left: 2px;
                }}
            """)

    def set_active(self, active: bool):
        self._active = active
        self.setChecked(active)
        self._accent_bar.setVisible(active)
        self._apply_style(active)
        # update icon/text color
        if active:
            self._ic.setStyleSheet(f"background:transparent; border:none; color:{ACCENT_GLOW};")
            self._txt.setStyleSheet(f"background:transparent; border:none; color:{ACCENT_GLOW}; font-weight:700;")
        else:
            self._ic.setStyleSheet("background:transparent; border:none;")
            self._txt.setStyleSheet("background:transparent; border:none;")


# ─────────────────────────────────────────────────────────────────────────────
#  User info widget  (bottom of sidebar)
# ─────────────────────────────────────────────────────────────────────────────

class _UserWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(68)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build()

    def _build(self):
        h = QHBoxLayout(self)
        h.setContentsMargins(16, 8, 16, 8)
        h.setSpacing(12)

        # Avatar circle (painted)
        avatar = _AvatarCircle("A", "#6366f1")
        h.addWidget(avatar)

        info = QVBoxLayout()
        info.setSpacing(2)

        name = QLabel("Alex Morgan")
        name.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        name.setStyleSheet(f"color:{TEXT_PRIMARY}; background:transparent;")
        info.addWidget(name)

        plan_row = QHBoxLayout()
        plan_row.setSpacing(6)
        plan_dot = QLabel("●")
        plan_dot.setStyleSheet(f"color:#10b981; font-size:8px; background:transparent;")
        plan_row.addWidget(plan_dot)
        plan = QLabel("Pro Plan")
        plan.setFont(QFont("Segoe UI", 9))
        plan.setStyleSheet(f"color:{TEXT_MUTED}; background:transparent;")
        plan_row.addWidget(plan)
        plan_row.addStretch()
        info.addLayout(plan_row)

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

        # Gradient fill
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor("#6366f1"))
        grad.setColorAt(1.0, QColor("#a855f7"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
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
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0d1528, stop:1 {BG_SIDEBAR});
                border-right: 1px solid {BORDER};
                border-radius: 0px;
            }}
        """)

        self._nav_buttons: list[_NavButton] = []
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 0, 8, 0)
        v.setSpacing(0)

        # Logo
        v.addSpacing(8)
        v.addWidget(_LogoWidget())
        v.addSpacing(16)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{BORDER}; border:none;")
        v.addWidget(sep)
        v.addSpacing(14)

        # Section label
        section_lbl = QLabel("NAVIGATION")
        section_lbl.setFont(QFont("Segoe UI", 8))
        section_lbl.setStyleSheet(
            f"color:{TEXT_MUTED}; letter-spacing:2px; background:transparent; "
            f"padding-left: 16px;"
        )
        v.addWidget(section_lbl)
        v.addSpacing(8)

        # Nav items
        nav_items = [
            ("🏠", "Dashboard"),
            ("📊", "Analytics"),
            ("📅", "Planner"),
            ("⚡", "Focus Mode"),
            ("⚙", "Settings"),
            ("🧬", "AI Debug"),
        ]

        for i, (icon, label) in enumerate(nav_items):
            btn = _NavButton(icon, label, active=(i == 0))
            btn.clicked.connect(lambda checked, idx=i: self._switch(idx))
            self._nav_buttons.append(btn)
            v.addWidget(btn)
            v.addSpacing(2)

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
                    background: {BG_SIDEBAR};
                    border-right: none;
                    border-radius: 0px;
                }}
            """)
        else:
            new_width = 230
            self.setStyleSheet(f"""
                QFrame {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #0d1528, stop:1 {BG_SIDEBAR});
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

    # ── page loading ──────────────────────────────────────────────────────────
    def _load_pages(self):
        from ui.dashboard_page import DashboardPage
        from ui.analytics_page import AnalyticsPage
        from ui.planner_page import PlannerPage
        from ui.focus_mode_page import FocusModePage
        from ui.settings_page import SettingsPage
        from ui.ai_debug_page import AIDebugPage

        self._dash_page  = DashboardPage()
        self._analytics  = AnalyticsPage()
        self._planner = PlannerPage()
        self._focus_mode = FocusModePage()
        self._settings = SettingsPage()
        self._ai_debug = AIDebugPage()

        for page in [
            self._dash_page,
            self._analytics,
            self._planner,
            self._focus_mode,
            self._settings,
            self._ai_debug,
        ]:
            self._stack.addWidget(page)

    def _on_nav_change(self, index: int):
        self._stack.setCurrentIndex(index)
        if index == 2 and hasattr(self, "_planner"):
            self._planner.refresh_tasks()
        if index == 3 and hasattr(self, "_focus_mode"):
            self._focus_mode._poll_focus_state()

    def set_engine(self, engine):
        self._engine = engine
        if hasattr(self, "_dash_page") and self._dash_page:
            self._dash_page.set_engine(engine)
        if hasattr(self, "_focus_mode") and self._focus_mode:
            self._focus_mode.set_engine(engine)
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
