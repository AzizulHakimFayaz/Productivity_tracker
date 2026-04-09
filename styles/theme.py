# ── Colour palette ────────────────────────────────────────────────────────────
BG_MAIN       = "#0f172a"
BG_SIDEBAR    = "#0f172a"
BG_CARD       = "#1e293b"
BG_CARD_ALT   = "#334155"
BG_INPUT      = "#1e293b"
BORDER        = "#334155"
BORDER_LIGHT  = "#475569"

ACCENT        = "#6366f1"
ACCENT_DARK   = "#4f46e5"
ACCENT_PURPLE = "#a855f7"
ACCENT_PURPLE_DARK = "#9333ea"
ACTIVE_CARD   = "#4f46e5" 

TEXT_PRIMARY   = "#f8fafc"
TEXT_SECONDARY = "#cbd5e1"
TEXT_MUTED     = "#94a3b8"

GREEN   = "#10b981"
YELLOW  = "#eab308"
DANGER  = "#ef4444"
ORANGE  = "#f97316"
PINK    = "#ec4899"
SLATE   = "#64748b"
CYAN    = "#06b6d4"
TEAL    = "#14b8a6"

# ── Reusable QSS snippets ─────────────────────────────────────────────────────
def card_style(bg=BG_CARD, radius=12, border=BORDER):
    return f"""
        background-color: {bg};
        border: 1px solid {border};
        border-radius: {radius}px;
    """

def label_style(color=TEXT_PRIMARY, size=10, bold=False):
    weight = "bold" if bold else "normal"
    return f"color: {color}; font-size: {size}px; font-weight: {weight};"

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
    background: {BG_CARD};
    width: 6px;
    border-radius: 3px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    border: none;
    background: none;
    height: 0;
}}
QScrollBar:horizontal {{
    border: none;
    background: {BG_CARD};
    height: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 3px;
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
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 12px;
}}

/* ── QLabel reset – prevent border inheritance from QFrame parents ── */
QLabel {{
    border: none;
    background: transparent;
}}

/* ── Extra guard for card/frame contents ── */
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

/* ── Context menu polish ── */
QMenu {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    background: transparent;
    border-radius: 6px;
    padding: 8px 12px;
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
"""
