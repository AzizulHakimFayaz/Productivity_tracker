from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, QRectF, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush, QLinearGradient
from PyQt6.QtWidgets import (
    QBoxLayout, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget, QCheckBox,
    QListWidget, QListWidgetItem,
)
import datetime
from ui.task_dialog import CreateTaskDialog

from styles.theme import (
    ACCENT, ACCENT_PURPLE, BG_CARD, BG_CARD_ALT, BG_MAIN, BORDER, BORDER_LIGHT,
    CYAN, GREEN, ORANGE, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, YELLOW,
)
from ui.ui_effects import apply_soft_shadow
from widgets.focus_mode import CategoryTagSelector, DEFAULT_WARNING_CATEGORIES, category_label


# ──────────────────────────────────────────────────────────────────────────────
#  Focus Mode Presets  (static data — AI hooks marked TODO)
# ──────────────────────────────────────────────────────────────────────────────
FOCUS_MODE_PRESETS: dict[str, dict] = {
    "study": {
        "label": "Study",
        "icon": "📚",
        "color": "#3b82f6",
        "description": "Deep reading & learning sessions",
        "sprint_default": 50,
        "break_default": 10,
        # TODO: replace with AI-generated context-aware nudges
        "nudges": [
            "Stop reading — give your brain a 10-min rest.",
            "Memory consolidates during breaks. Step away!",
            "Look 20 feet away for 20 seconds.",
            "Stretch your neck and shoulders.",
            "Jot down 3 things you just learned.",
        ],
    },
    "coding": {
        "label": "Coding",
        "icon": "💻",
        "color": CYAN,
        "description": "Deep work on software & engineering",
        "sprint_default": 90,
        "break_default": 15,
        "nudges": [
            "Step away — your eyes need rest.",
            "Take a walk. Fresh ideas come on breaks.",
            "Hydrate! You've been coding for a while.",
            "Stretch your wrists and fingers.",
            "Commit your work and take a breather.",
        ],
    },
    "workout": {
        "label": "Workout",
        "icon": "🏋️",
        "color": ORANGE,
        "description": "Training, exercise & movement",
        "sprint_default": 45,
        "break_default": 5,
        "nudges": [
            "Hydrate now — drink some water.",
            "Rest your muscles before the next set.",
            "Check your form and breathing.",
            "Great effort! Recover between sets.",
            "Cool down — your body will thank you.",
        ],
    },
    "writing": {
        "label": "Writing",
        "icon": "✍️",
        "color": "#f59e0b",
        "description": "Essays, docs, creative & long-form writing",
        "sprint_default": 60,
        "break_default": 10,
        "nudges": [
            "Stop writing — let your thoughts breathe.",
            "Walk around. Fresh perspective incoming.",
            "Rest your hands and wrists.",
            "Read back what you wrote so far.",
            "Close your eyes, visualize your next paragraph.",
        ],
    },
    "deep_work": {
        "label": "Deep Work",
        "icon": "🧠",
        "color": ACCENT_PURPLE,
        "description": "High-focus cognitively demanding tasks",
        "sprint_default": 120,
        "break_default": 20,
        "nudges": [
            "Surface for air — mindful 5-min break.",
            "Your focus battery needs recharging.",
            "Step outside. Nature resets the mind.",
            "Breathe deeply 5×, then continue.",
            "Grab water and stretch before the next sprint.",
        ],
    },
}


def _label(text: str, size: int = 12, bold: bool = False,
           color: str = TEXT_PRIMARY, wrap: bool = False) -> QLabel:
    w = QLabel(text)
    w.setFont(QFont("Segoe UI", size, QFont.Weight.Bold if bold else QFont.Weight.Normal))
    w.setStyleSheet(f"color:{color}; background:transparent; border:none;")
    if wrap:
        w.setWordWrap(True)
    return w


def _fmt(seconds: int) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m = rem // 60
    return f"{h}h {m:02d}m" if h else f"{m}m"


def _hsep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFixedHeight(1)
    f.setStyleSheet(f"background:{BORDER}; border:none;")
    return f


# ──────────────────────────────────────────────────────────────────────────────
#  MinutePicker — modern popup dropdown
# ──────────────────────────────────────────────────────────────────────────────
class MinutePicker(QWidget):
    value_changed = pyqtSignal(int)

    def __init__(self, value: int = 90, presets: list[int] = None, parent=None):
        super().__init__(parent)
        self._value = value
        self._presets = presets or [5, 10, 15, 20, 30, 45, 60, 90]
        self._build()

    def _build(self):
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        self._btn = QPushButton(f"[{self._value} min]")
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.setFixedHeight(30)
        self._btn.setMinimumWidth(100)
        self._btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {CYAN};
                border: 1px solid {BORDER}; border-radius: 8px;
                padding: 0 12px; font-size: 12px; font-weight: 700;
                text-align: right;
            }}
            QPushButton:hover {{ background: rgba(34,211,238,.07); border: 1px solid {CYAN}55; }}
        """)
        self._btn.clicked.connect(self._show)
        h.addWidget(self._btn)

    def value(self) -> int:
        return self._value

    def setValue(self, v: int):
        self._value = v
        self._btn.setText(f"[{v} min]")

    def _show(self):
        popup = QFrame(self, Qt.WindowType.Popup)
        popup.setFixedWidth(224)
        popup.setStyleSheet(f"""
            QFrame {{
                background: #0d1b2a;
                border: 1px solid {BORDER_LIGHT};
                border-radius: 14px;
            }}
        """)
        apply_soft_shadow(popup, blur_radius=20, offset_y=8, alpha=130)

        out = QVBoxLayout(popup)
        out.setContentsMargins(10, 10, 10, 10)
        out.setSpacing(8)

        hdr = QLabel("SELECT MINUTES")
        hdr.setStyleSheet(f"color:{TEXT_MUTED}; font-size:8px; font-weight:700; letter-spacing:2px; background:transparent; border:none;")
        out.addWidget(hdr)

        gw = QWidget()
        gw.setStyleSheet("background:transparent;")
        grid = QGridLayout(gw)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(5)

        for i, p in enumerate(self._presets):
            r, c = divmod(i, 4)
            sel = p == self._value
            b = QPushButton(str(p))
            b.setFixedSize(44, 30)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"""
                QPushButton {{
                    background: {"rgba(34,211,238,.16)" if sel else "#131e2c"};
                    color: {"#22d3ee" if sel else TEXT_SECONDARY};
                    border: 1px solid {"rgba(34,211,238,.55)" if sel else BORDER};
                    border-radius: 7px; font-size: 11px; font-weight: {"700" if sel else "600"};
                }}
                QPushButton:hover {{ background: rgba(34,211,238,.1); color:#22d3ee; border:1px solid rgba(34,211,238,.4); }}
            """)

            def _click(_, val=p, pop=popup):
                self._value = val
                self._btn.setText(f"[{val} min]")
                self.value_changed.emit(val)
                pop.close()

            b.clicked.connect(_click)
            grid.addWidget(b, r, c)

        out.addWidget(gw)
        popup.adjustSize()
        gp = self._btn.mapToGlobal(self._btn.rect().bottomRight())
        popup.move(gp.x() - popup.width(), gp.y() + 4)
        popup.show()


# ──────────────────────────────────────────────────────────────────────────────
#  Glow Circular Timer
# ──────────────────────────────────────────────────────────────────────────────
class GlowCircularTimer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 1.0
        self._time_text = "1h 30m"
        self._sub = "Remaining"
        self._detail = "1h 30m left"
        self._pct = "100% (remaining)"
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_data(self, progress, time_text, sub, detail, pct):
        self._progress = max(0.0, min(1.0, progress))
        self._time_text = time_text
        self._sub = sub
        self._detail = detail
        self._pct = pct
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        radius = min(w, h) / 2.0 - 22

        for rp, alpha in [(28, 8), (18, 16), (8, 26)]:
            c = QColor("#22d3ee"); c.setAlpha(alpha)
            r = radius + rp
            p.setPen(QPen(c, 1)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        tp = QPen(QColor("#0f2030"), 14); tp.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(tp); p.drawArc(rect, int(225 * 16), int(-270 * 16))

        if self._progress:
            pp = QPen(QColor("#22d3ee"), 14); pp.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pp); p.drawArc(rect, int(225 * 16), int(-self._progress * 270 * 16))

        p.setPen(QColor(TEXT_PRIMARY))
        p.setFont(QFont("Segoe UI", int(radius * 0.30), QFont.Weight.Bold))
        p.drawText(QRectF(cx - radius, cy - radius * 0.52, radius * 2, radius * 0.52),
                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, self._time_text)

        p.setPen(QColor(TEXT_SECONDARY))
        p.setFont(QFont("Segoe UI", int(radius * 0.115)))
        p.drawText(QRectF(cx - radius, cy + radius * 0.02, radius * 2, radius * 0.28),
                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, self._sub)

        p.setPen(QColor(TEXT_MUTED))
        p.setFont(QFont("Segoe UI", int(radius * 0.10)))
        p.drawText(QRectF(cx - radius, cy + radius * 0.26, radius * 2, radius * 0.24),
                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, self._detail)
        p.drawText(QRectF(cx - radius, cy + radius * 0.44, radius * 2, radius * 0.24),
                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, self._pct)
        p.end()


# ──────────────────────────────────────────────────────────────────────────────
#  Focus Mode Page
# ──────────────────────────────────────────────────────────────────────────────
class FocusModePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{BG_MAIN};")
        self._engine = None
        self._syncing = False
        self._active_mode = "coding"
        self._nudge_idx = 0

        self._nudge_timer = QTimer(self)
        self._nudge_timer.timeout.connect(self._cycle_nudge)
        self._nudge_timer.start(8000)

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_focus_state)
        self._poll_timer.start(1000)
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────
    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        outer.addWidget(scroll)

        container = QWidget()
        container.setStyleSheet(f"background:{BG_MAIN};")
        scroll.setWidget(container)

        root = QVBoxLayout(container)
        root.setContentsMargins(28, 22, 28, 28)
        root.setSpacing(16)

        # ── Page header ────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.addWidget(_label("Focus Mode", 22, bold=True))
        self.status_badge = QLabel("OFF")
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge(self.status_badge, False)
        hdr.addWidget(self.status_badge, alignment=Qt.AlignmentFlag.AlignVCenter)
        hdr.addStretch()
        root.addLayout(hdr)

        # ── TOP ROW: left = hero/timer, right = mode selector & sprint config ─
        top_right_col = QVBoxLayout()
        top_right_col.setSpacing(16)
        top_right_col.addWidget(self._build_mode_panel())
        top_right_col.addWidget(self._build_sprint_config())

        top_row = QHBoxLayout()
        top_row.setSpacing(16)
        top_row.addWidget(self._build_hero(), 1)
        top_row.addLayout(top_right_col, 1)
        root.addLayout(top_row)

        # ── BOTTOM ROW: left = tasks, right = focus params ────────────────────
        bot_row = QHBoxLayout()
        bot_row.setSpacing(16)
        self._content_layout = bot_row
        bot_row.addWidget(self._build_task_panel(), 1)
        bot_row.addWidget(self._build_focus_params(), 1)
        root.addLayout(bot_row)

    # ── Hero (left top) ───────────────────────────────────────────────────────
    def _build_hero(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #07101e, stop:0.55 #0b1624, stop:1 #081220);
                border: 1px solid #1c2f48;
                border-radius: 18px;
            }
        """)
        apply_soft_shadow(card, blur_radius=28, offset_y=8, alpha=90)

        v = QVBoxLayout(card)
        v.setContentsMargins(22, 14, 22, 16)
        v.setSpacing(10)

        # Label
        sec = QLabel("FOCUS CONTROL CENTER")
        sec.setStyleSheet(f"color:{TEXT_MUTED}; font-size:9px; font-weight:700; letter-spacing:2px; background:transparent; border:none;")
        v.addWidget(sec)

        # Info: logged time + activity
        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        self.logged_time_lbl = QLabel("Logged Time: <b>0m</b>")
        self.logged_time_lbl.setTextFormat(Qt.TextFormat.RichText)
        self.logged_time_lbl.setStyleSheet(f"color:{TEXT_SECONDARY}; font-size:12px; background:transparent; border:none;")
        info_col.addWidget(self.logged_time_lbl)
        info_col.addWidget(_label("Current Activity:", 10, color=TEXT_MUTED))
        self.current_activity_lbl = _label("Waiting for tracker data", 13, bold=True)
        self.current_activity_lbl.setWordWrap(True)
        info_col.addWidget(self.current_activity_lbl)
        v.addLayout(info_col)

        # Timer centered
        timer_row = QHBoxLayout()
        timer_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.glow_timer = GlowCircularTimer()
        self.glow_timer.setFixedSize(210, 210)
        timer_row.addWidget(self.glow_timer, alignment=Qt.AlignmentFlag.AlignCenter)
        v.addLayout(timer_row)

        # Next break badge (shown when active)
        badge_row = QHBoxLayout()
        badge_row.addStretch()
        self.break_eta_lbl = QLabel("Next break in 30m")
        self.break_eta_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.break_eta_lbl.setStyleSheet(
            "color:#f59e0b; background:rgba(245,158,11,.10);"
            "border:1px solid rgba(245,158,11,.35); border-radius:12px;"
            "padding:5px 16px; font-size:11px; font-weight:600;"
        )
        self.break_eta_lbl.setVisible(False)
        badge_row.addWidget(self.break_eta_lbl)
        v.addLayout(badge_row)

        v.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        self.toggle_btn = QPushButton("Start Focus Mode")
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setFixedHeight(40)
        self._toggle_style(False)
        self.toggle_btn.clicked.connect(self._toggle_focus_mode)
        btn_row.addWidget(self.toggle_btn)
        btn_row.addStretch()
        self.save_btn = QPushButton("Save Setup")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setFixedHeight(40)
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #182d45, stop:1 #1c3855);
                color:#22d3ee; border:1px solid rgba(34,211,238,.27);
                border-radius:10px; padding:0 24px; font-weight:600; font-size:12px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #1e3a5c, stop:1 #254872);
                border:1px solid rgba(34,211,238,.5);
            }}
        """)
        self.save_btn.clicked.connect(self._save_focus_setup)
        btn_row.addWidget(self.save_btn)
        v.addLayout(btn_row)
        return card

    # ── Mode selector (right top) ─────────────────────────────────────────────
    def _build_mode_panel(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 18px;
            }}
        """)
        apply_soft_shadow(card, blur_radius=28, offset_y=8, alpha=80)

        v = QVBoxLayout(card)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(12)

        sec = QLabel("FOCUS MODE")
        sec.setStyleSheet(f"color:{TEXT_MUTED}; font-size:9px; font-weight:700; letter-spacing:2px; background:transparent; border:none;")
        v.addWidget(sec)

        # 2-column grid of mode cards
        self._mode_btns: dict[str, QPushButton] = {}
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(0, 0, 0, 0)

        for i, (key, meta) in enumerate(FOCUS_MODE_PRESETS.items()):
            row, col = divmod(i, 2)
            btn = self._make_mode_card(key, meta)
            self._mode_btns[key] = btn
            grid.addWidget(btn, row, col)

        v.addLayout(grid)

        # Mode description
        self.mode_desc = QLabel("")
        self.mode_desc.setWordWrap(True)
        self.mode_desc.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px; font-style:italic; background:transparent; border:none;")
        v.addWidget(self.mode_desc)

        v.addWidget(_hsep())

        # Nudge preview (cycles every 8s)
        nudge_label = QLabel("NEXT BREAK MESSAGE PREVIEW")
        nudge_label.setStyleSheet(f"color:{TEXT_MUTED}; font-size:8px; font-weight:700; letter-spacing:2px; background:transparent; border:none;")
        v.addWidget(nudge_label)

        self.nudge_bar = QLabel("Loading...")
        self.nudge_bar.setWordWrap(True)
        self.nudge_bar.setStyleSheet(f"""
            color:{TEXT_SECONDARY};
            background:{BG_CARD_ALT};
            border:1px solid {BORDER};
            border-radius:10px;
            padding:10px 14px;
            font-size:11px;
            font-style:italic;
        """)
        v.addWidget(self.nudge_bar)

        v.addStretch()

        # Apply initial mode
        self._select_mode(self._active_mode)
        return card

    def _make_mode_card(self, key: str, meta: dict) -> QPushButton:
        color = meta["color"]
        btn = QPushButton(f"  {meta['icon']}  {meta['label']}")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(44)
        btn.setCheckable(True)
        btn.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        # Default (unselected) style stored; will be overridden by _select_mode
        btn.setStyleSheet(f"""
            QPushButton {{
                background:#131e2c; color:{TEXT_MUTED};
                border:1.5px solid {BORDER}; border-radius:11px;
                text-align:left; padding-left:12px;
            }}
            QPushButton:hover {{
                background:{color}14; color:{color};
                border:1.5px solid {color}44;
            }}
        """)
        btn.clicked.connect(lambda _, k=key: self._select_mode(k))
        return btn

    def _select_mode(self, key: str):
        self._active_mode = key
        meta = FOCUS_MODE_PRESETS[key]

        for k, btn in self._mode_btns.items():
            m = FOCUS_MODE_PRESETS[k]
            c = m["color"]
            if k == key:
                btn.setChecked(True)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                            stop:0 {c}28, stop:1 {c}10);
                        color:{c};
                        border:1.5px solid {c}88;
                        border-radius:11px;
                        text-align:left; padding-left:12px;
                        font-weight:700;
                    }}
                """)
            else:
                btn.setChecked(False)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background:#131e2c; color:{TEXT_MUTED};
                        border:1.5px solid {BORDER}; border-radius:11px;
                        text-align:left; padding-left:12px;
                    }}
                    QPushButton:hover {{
                        background:{c}14; color:{c};
                        border:1.5px solid {c}44;
                    }}
                """)

        if hasattr(self, "mode_desc"):
            self.mode_desc.setText(meta["description"])

        # Auto-fill sprint/break defaults
        if hasattr(self, "session_minutes"):
            self.session_minutes.setValue(meta["sprint_default"])
        if hasattr(self, "break_duration"):
            self.break_duration.setValue(meta["break_default"])

        self._nudge_idx = 0
        if hasattr(self, "nudge_bar"):
            self._update_nudge()

    def _update_nudge(self):
        meta = FOCUS_MODE_PRESETS.get(self._active_mode, {})
        nudges = meta.get("nudges", [])
        if nudges:
            # TODO: swap with AI-generated message when AI module is connected
            msg = nudges[self._nudge_idx % len(nudges)]
            icon = meta.get("icon", "💡")
            self.nudge_bar.setText(f"{icon}  {msg}")
            self._nudge_idx += 1

    def _cycle_nudge(self):
        if hasattr(self, "nudge_bar"):
            self._update_nudge()

    # ── Sprint Config (left bottom) ────────────────────────────────────────────
    def _build_sprint_config(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{ background:{BG_CARD}; border:1px solid {BORDER}; border-radius:16px; }}
        """)
        apply_soft_shadow(card, blur_radius=22, offset_y=6, alpha=60)

        v = QVBoxLayout(card)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(12)

        sec = QLabel("SESSION CONFIGURATION")
        sec.setStyleSheet(f"color:{TEXT_MUTED}; font-size:9px; font-weight:700; letter-spacing:2px; background:transparent; border:none;")
        v.addWidget(sec)

        inner = QFrame()
        inner.setStyleSheet(f"QFrame{{ background:{BG_CARD_ALT}; border:1px solid {BORDER}; border-radius:12px; }}")
        iv = QVBoxLayout(inner)
        iv.setContentsMargins(16, 14, 16, 14)
        iv.setSpacing(0)

        d = QLabel("SPRINT DESIGNER")
        d.setStyleSheet(f"color:{TEXT_MUTED}; font-size:9px; font-weight:700; letter-spacing:2px; background:transparent; border:none;")
        iv.addWidget(d)
        iv.addSpacing(14)

        sl = QHBoxLayout()
        sl.addWidget(_label("Sprint Length", 11, color=TEXT_SECONDARY))
        sl.addStretch()
        self.session_minutes = MinutePicker(90, [15,20,25,30,45,60,75,90,105,120,150,180])
        sl.addWidget(self.session_minutes)
        iv.addLayout(sl)
        iv.addSpacing(10)
        iv.addWidget(_hsep())
        iv.addSpacing(10)

        bl = QHBoxLayout()
        bl.addWidget(_label("Break Length", 11, color=TEXT_SECONDARY))
        bl.addStretch()
        self.break_duration = MinutePicker(5, [1,2,3,5,7,10,15,20])
        bl.addWidget(self.break_duration)
        iv.addLayout(bl)
        iv.addStretch()

        v.addWidget(inner)

        self.sprint_note = QLabel("Auto-finishes the sprint.\nBreak per nudge interval.")
        self.sprint_note.setWordWrap(True)
        self.sprint_note.setStyleSheet(f"""
            color:{TEXT_MUTED}; background:{BG_CARD_ALT};
            border:1px solid {BORDER}; border-radius:10px;
            padding:11px 16px; font-size:11px;
        """)
        v.addWidget(self.sprint_note)
        v.addStretch()
        return card

    def _build_task_panel(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{ background:{BG_CARD}; border:1px solid {BORDER}; border-radius:16px; }}
        """)
        apply_soft_shadow(card, blur_radius=22, offset_y=6, alpha=60)
        v = QVBoxLayout(card)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(12)

        hdr = QHBoxLayout()
        sec = QLabel("TASKS")
        sec.setStyleSheet(f"color:{TEXT_MUTED}; font-size:9px; font-weight:700; letter-spacing:2px; background:transparent; border:none;")
        hdr.addWidget(sec)
        hdr.addStretch()
        
        self.add_task_btn = QPushButton("+ Add")
        self.add_task_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_task_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #22d3aa; color: white;
                border: none; border-radius: 6px;
                padding: 4px 10px; font-weight: bold; font-size: 10px;
            }}
            QPushButton:hover {{ background-color: #2ee6bc; }}
        """)
        self.add_task_btn.clicked.connect(self._show_create_task_dialog)
        hdr.addWidget(self.add_task_btn)
        v.addLayout(hdr)

        self.task_list = QListWidget()
        self.task_list.setStyleSheet(f"""
            QListWidget {{
                background:#0f1b31;
                border:1px solid #2b3b57;
                border-radius:12px;
                color:{TEXT_PRIMARY};
            }}
            QListWidget::item {{
                border-bottom: 1px solid #22324c;
                padding: 8px 6px;
            }}
            QListWidget::item:selected {{ background: #233a57; }}
        """)
        v.addWidget(self.task_list)
        return card

    def _show_create_task_dialog(self):
        if not self._engine: return
        dlg = CreateTaskDialog(self._engine, self)
        if dlg.exec():
            self.refresh_tasks()

    def refresh_tasks(self):
        if not hasattr(self, "task_list") or not self._engine:
            return
        all_tasks = self._engine.db_manager.get_tasks()
        tasks = [t for t in all_tasks if t["status"] == "pending"]
        self.task_list.clear()
        now = datetime.datetime.now().timestamp()
        for t in tasks:
            due_dt = datetime.datetime.fromtimestamp(t["due_ts"])
            due_txt = due_dt.strftime("%d %b %Y, %I:%M %p")
            overdue = (t["status"] == "pending" and t["due_ts"] < now)
            badge = "OVERDUE" if overdue else "PENDING"
            pri = str(t.get("priority", "medium")).upper()
            desc = t["description"].strip()
            icon = "⚠" if overdue else "🗂"
            line1 = f"{icon} [{badge}]  {t['title']}  •  {pri}"
            line2 = f"Due: {due_txt}"
            text = line1 + "\n" + line2 + (f"\n{desc}" if desc else "")
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, t["id"])
            if overdue: item.setForeground(Qt.GlobalColor.red)
            self.task_list.addItem(item)
        if not tasks:
            empty_item = QListWidgetItem("📄  No pending tasks.")
            empty_item.setForeground(QColor("#93a4c4"))
            self.task_list.addItem(empty_item)

    # ── Focus Params (right bottom) ────────────────────────────────────────────
    def _build_focus_params(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{ background:{BG_CARD}; border:1px solid {BORDER}; border-radius:16px; }}
        """)
        apply_soft_shadow(card, blur_radius=22, offset_y=6, alpha=60)

        v = QVBoxLayout(card)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(12)

        sec = QLabel("FOCUS PARAMETERS")
        sec.setStyleSheet(f"color:{TEXT_MUTED}; font-size:9px; font-weight:700; letter-spacing:2px; background:transparent; border:none;")
        v.addWidget(sec)

        wl = QLabel("DISTRACTION WATCHLIST")
        wl.setStyleSheet(f"color:{TEXT_MUTED}; font-size:9px; font-weight:700; letter-spacing:2px; background:transparent; border:none;")
        v.addWidget(wl)

        self.warning_categories = CategoryTagSelector()
        v.addWidget(self.warning_categories)

        self.watchlist_note = _label("2 categories: Entertainment, Browsing", 10, color=TEXT_MUTED)
        v.addWidget(self.watchlist_note)

        v.addWidget(_hsep())

        rl = QLabel("RHYTHM & NUDGES")
        rl.setStyleSheet(f"color:{TEXT_MUTED}; font-size:9px; font-weight:700; letter-spacing:2px; background:transparent; border:none;")
        v.addWidget(rl)

        tr = QHBoxLayout()
        tr.setSpacing(10)
        self.break_enabled = QCheckBox()
        self.break_enabled.setChecked(True)
        self.break_enabled.setStyleSheet(f"""
            QCheckBox::indicator {{
                width:36px; height:18px; border-radius:9px;
                border:1px solid {BORDER_LIGHT}; background:{BG_CARD_ALT};
            }}
            QCheckBox::indicator:checked {{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #22d3ee, stop:1 #0ea5e9);
                border:1px solid #22d3ee;
            }}
        """)
        tr.addWidget(self.break_enabled)
        el = QLabel("ENABLE SMART BREAK REMINDERS")
        el.setStyleSheet(f"color:{TEXT_PRIMARY}; font-size:10px; font-weight:700; letter-spacing:1px; background:transparent; border:none;")
        tr.addWidget(el)
        tr.addStretch()
        v.addLayout(tr)

        rr = QHBoxLayout()
        rr.addWidget(_label("Remind me after:", 11, color=TEXT_SECONDARY))
        self.break_interval = MinutePicker(10, [5,10,15,20,25,30,45,60])
        rr.addWidget(self.break_interval)
        rr.addStretch()
        v.addLayout(rr)

        wr = QHBoxLayout()
        wr.addWidget(_label("Distraction warning:", 11, color=TEXT_SECONDARY))
        self.warning_threshold = MinutePicker(3, [1,2,3,5,7,10,15,20])
        wr.addWidget(self.warning_threshold)
        wr.addStretch()
        v.addLayout(wr)

        v.addWidget(_hsep())
        v.addWidget(self._build_playbook())
        v.addStretch()
        return card

    def _build_playbook(self) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet(f"QFrame{{ background:{BG_CARD_ALT}; border:1px solid {BORDER}; border-radius:12px; }}")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)

        t = QLabel("HOW THIS SPRINT WORKS")
        t.setStyleSheet(f"color:{TEXT_MUTED}; font-size:9px; font-weight:700; letter-spacing:2px; background:transparent; border:none;")
        lay.addWidget(t)

        row = QHBoxLayout()
        for icon, lbl, color in [("▶","Start",CYAN),("⟳","Drift",ORANGE),("↺","Reset",TEXT_SECONDARY),("✓","Finish",GREEN)]:
            col = QVBoxLayout()
            col.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.setSpacing(5)
            b = QPushButton(icon)
            b.setFixedSize(44, 44)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"""
                QPushButton {{ background:{color}1a; color:{color}; border:1px solid {color}44;
                    border-radius:22px; font-size:16px; font-weight:700; }}
                QPushButton:hover {{ background:{color}33; border:1px solid {color}88; }}
            """)
            col.addWidget(b, alignment=Qt.AlignmentFlag.AlignCenter)
            lbl_w = _label(lbl, 9, color=TEXT_MUTED)
            lbl_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.addWidget(lbl_w, alignment=Qt.AlignmentFlag.AlignCenter)
            row.addLayout(col)
        lay.addLayout(row)
        return panel

    # ── Badge / button helpers ────────────────────────────────────────────────
    def _badge(self, w: QLabel, active: bool):
        if active:
            w.setText("ACTIVE")
            w.setStyleSheet("color:#22d3ee; background:rgba(34,211,238,.13); border:1px solid rgba(34,211,238,.33); border-radius:10px; padding:3px 12px; font-size:10px; font-weight:700; letter-spacing:1px;")
        else:
            w.setText("OFF")
            w.setStyleSheet(f"color:{TEXT_MUTED}; background:{BG_CARD_ALT}; border:1px solid {BORDER}; border-radius:10px; padding:3px 12px; font-size:10px; font-weight:700; letter-spacing:1px;")

    def _toggle_style(self, active: bool):
        if active:
            self.toggle_btn.setText("End Focus Mode")
            self.toggle_btn.setStyleSheet("QPushButton { background:#0d2538; color:#22d3ee; border:1px solid rgba(34,211,238,.33); border-radius:10px; padding:0 22px; font-weight:700; font-size:12px; } QPushButton:hover { background:#113044; }")
        else:
            self.toggle_btn.setText("Start Focus Mode")
            self.toggle_btn.setStyleSheet("QPushButton { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #6366f1,stop:1 #a855f7); color:white; border:none; border-radius:10px; padding:0 22px; font-weight:700; font-size:12px; } QPushButton:hover { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #818cf8,stop:1 #c084fc); }")

    # ── Engine ─────────────────────────────────────────────────────────────────
    def set_engine(self, engine):
        self._engine = engine
        if not engine:
            return
        try: engine.settings_changed.connect(self._load_setup)
        except TypeError: pass
        try: engine.current_activity_changed.connect(self._on_activity)
        except TypeError: pass
        self._load_setup(engine.get_settings())
        self._poll_focus_state()
        self.refresh_tasks()

    def _collect(self) -> dict:
        return {
            "focus_session_minutes": self.session_minutes.value(),
            "focus_break_reminders_enabled": self.break_enabled.isChecked(),
            "focus_break_interval_minutes": self.break_interval.value(),
            "focus_break_duration_minutes": self.break_duration.value(),
            "warning_categories": self.warning_categories.categories(),
            "warning_threshold_minutes": self.warning_threshold.value(),
            "warning_cooldown_minutes": 30,
            "focus_mode_preset": self._active_mode,
        }

    def _save_focus_setup(self):
        if not self._engine: return
        p = self._collect()
        p["focus_mode_enabled"] = bool(self._engine.get_focus_mode_state().get("enabled", False))
        self._engine.update_settings(p)

    def _toggle_focus_mode(self):
        if not self._engine: return
        state = self._engine.get_focus_mode_state()
        p = self._collect()
        p["focus_mode_enabled"] = not bool(state.get("enabled", False))
        self._engine.update_settings(p)
        self._poll_focus_state()

    def _load_setup(self, s: dict):
        self._syncing = True
        self.session_minutes.setValue(int(s.get("focus_session_minutes", 90)))
        self.break_enabled.setChecked(bool(s.get("focus_break_reminders_enabled", True)))
        self.break_interval.setValue(int(s.get("focus_break_interval_minutes", 10)))
        self.break_duration.setValue(int(s.get("focus_break_duration_minutes", 5)))
        self.warning_threshold.setValue(int(s.get("warning_threshold_minutes", 3)))
        pk = s.get("focus_mode_preset", "coding")
        if pk in FOCUS_MODE_PRESETS:
            self._select_mode(pk)
        self.warning_categories.set_categories(
            s.get("warning_categories", DEFAULT_WARNING_CATEGORIES), emit_signal=False)
        self._syncing = False

    def _on_activity(self, app: str, title: str, domain: str, cat: str):
        if title:
            self.current_activity_lbl.setText(title[:40] if len(title) <= 40 else title[:37] + "...")

    def _poll_focus_state(self):
        if not self._engine: return
        st = self._engine.get_focus_mode_state()
        enabled = bool(st.get("enabled", False))
        pct = int(st.get("progress_pct", 0))
        rem = int(st.get("remaining_secs", 0))
        ela = int(st.get("elapsed_secs", 0))
        nxt = int(st.get("next_break_secs", 0))
        smin = int(st.get("focus_session_minutes", 90))
        title = str(st.get("active_title", ""))

        rem_lbl = _fmt(rem) if enabled else f"{smin}m"
        self.glow_timer.set_data(
            progress=(100 - pct) / 100.0 if enabled else 1.0,
            time_text=rem_lbl,
            sub="Remaining" if enabled else "Ready",
            detail=f"{rem_lbl} left" if enabled else f"{smin} min sprint",
            pct=f"{max(0,100-pct)}% (remaining)" if enabled else "Press Start to begin",
        )

        self.logged_time_lbl.setText(f"Logged Time: <b>{_fmt(ela)}</b>")
        self.current_activity_lbl.setText(
            (title[:40] if len(title) <= 40 else title[:37] + "...") if title else "Waiting for tracker data"
        )

        if enabled and bool(st.get("break_reminders_enabled", True)):
            self.break_eta_lbl.setText(f"Next break in <b>{_fmt(nxt)}</b>")
            self.break_eta_lbl.setTextFormat(Qt.TextFormat.RichText)
            self.break_eta_lbl.setVisible(True)
        else:
            self.break_eta_lbl.setVisible(False)

        self._badge(self.status_badge, enabled)
        self._toggle_style(enabled)

        cats = st.get("warning_categories", [])
        n = len(cats)
        self.watchlist_note.setText(
            f"{n} {'category' if n==1 else 'categories'}: " + ", ".join(category_label(c) for c in cats)
            if cats else "No categories selected"
        )

        interval = int(st.get("break_interval_minutes", 10))
        self.sprint_note.setText(
            f"Auto-finishes the sprint.\nBreak every {interval} min (as configured in Nudges)."
        )

    def resizeEvent(self, e):
        super().resizeEvent(e)
