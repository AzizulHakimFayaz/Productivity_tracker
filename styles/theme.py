# ── Colour palette ────────────────────────────────────────────────────────────
BG_MAIN       = "#080f1e"
BG_SIDEBAR    = "#0a1122"
BG_CARD       = "#111827"
BG_CARD_ALT   = "#1f2937"
BG_INPUT      = "#1f2937"
BORDER        = "#1e2d45"
BORDER_LIGHT  = "#2d4060"

ACCENT        = "#6366f1"
ACCENT_DARK   = "#4f46e5"
ACCENT_PURPLE = "#a855f7"
ACCENT_PURPLE_DARK = "#9333ea"
ACCENT_GLOW   = "#818cf8"
ACTIVE_CARD   = "#312e81"

TEXT_PRIMARY   = "#f1f5f9"
TEXT_SECONDARY = "#94a3b8"
TEXT_MUTED     = "#64748b"

GREEN   = "#10b981"
YELLOW  = "#f59e0b"
DANGER  = "#ef4444"
ORANGE  = "#f97316"
PINK    = "#ec4899"
SLATE   = "#475569"
CYAN    = "#22d3ee"
TEAL    = "#14b8a6"

# ── Reusable QSS snippets ─────────────────────────────────────────────────────
def card_style(bg=BG_CARD, radius=14, border=BORDER):
    return f"""
        background-color: {bg};
        border: 1px solid {border};
        border-radius: {radius}px;
    """

def label_style(color=TEXT_PRIMARY, size=10, bold=False):
    weight = "bold" if bold else "normal"
    return f"color: {color}; font-size: {size}px; font-weight: {weight};"

def gradient_card_style(accent=ACCENT, bg=BG_CARD, radius=14):
    """Card with a subtle top-left gradient tint."""
    return f"""
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 {accent}0a, stop:0.4 {bg}, stop:1 {bg});
        border: 1px solid {BORDER};
        border-radius: {radius}px;
    """

# ── Global application stylesheet ─────────────────────────────────────────────
APP_STYLE = f"""
/* ── Base ── */
QWidget {{
    background-color: {BG_MAIN};
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {BG_MAIN};
}}

/* ── Scrollbars ── */
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 5px;
    border-radius: 3px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_LIGHT};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    border: none;
    background: none;
    height: 0;
}}
QScrollBar:horizontal {{
    border: none;
    background: transparent;
    height: 5px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_LIGHT};
    border-radius: 3px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {ACCENT};
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    border: none;
    background: none;
    width: 0;
}}

/* ── Tooltips ── */
QToolTip {{
    background-color: {BG_CARD_ALT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_LIGHT};
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ── QLabel reset ── */
QLabel {{
    border: none;
    background: transparent;
}}

QFrame QLabel {{
    border: none;
    background: transparent;
}}

/* ── Selection polish ── */
QLabel::selection,
QLineEdit::selection,
QTextEdit::selection,
QPlainTextEdit::selection {{
    background: {ACCENT_DARK};
    color: white;
}}

/* ── Context menu ── */
QMenu {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_LIGHT};
    border-radius: 12px;
    padding: 6px;
}}
QMenu::item {{
    background: transparent;
    border-radius: 8px;
    padding: 8px 14px;
}}
QMenu::item:selected {{
    background-color: {BG_CARD_ALT};
    color: {TEXT_PRIMARY};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 6px 8px;
}}

/* ── Generic QPushButton reset ── */
QPushButton {{
    background-color: transparent;
    border: none;
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', Arial, sans-serif;
}}
QPushButton:focus {{
    outline: none;
}}

/* ── QCheckBox ── */
QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1.5px solid {BORDER_LIGHT};
    background: {BG_CARD_ALT};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border: 1.5px solid {ACCENT};
}}
"""
