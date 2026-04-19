from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QVBoxLayout,
)

from styles.theme import (
    ACCENT,
    BG_CARD,
    BG_CARD_ALT,
    BORDER,
    GREEN,
    ORANGE,
    PINK,
    SLATE,
    CYAN,
    TEAL,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    YELLOW,
    DANGER,
)


CATEGORY_META: dict[str, dict[str, str]] = {
    "coding": {
        "label": "Coding",
        "description": "IDEs, terminals, git, Docker, and software development work.",
        "color": "#3b82f6",
    },
    "learning": {
        "label": "Learning",
        "description": "Courses, research, documentation, tutorials, and study time.",
        "color": GREEN,
    },
    "writing": {
        "label": "Writing",
        "description": "Docs, notes, drafts, essays, and long-form writing sessions.",
        "color": YELLOW,
    },
    "communication": {
        "label": "Communication",
        "description": "Slack, Discord, email, and message-heavy collaboration windows.",
        "color": "#8b5cf6",
    },
    "entertainment": {
        "label": "Entertainment",
        "description": "Streaming, videos, games, music, and social feeds.",
        "color": DANGER,
    },
    "designing": {
        "label": "Designing",
        "description": "Figma, Photoshop, mockups, creative tools, and visual design.",
        "color": PINK,
    },
    "browsing": {
        "label": "Browsing",
        "description": "General surfing, search drift, news feeds, and unfocused tab hopping.",
        "color": SLATE,
    },
    "meetings": {
        "label": "Meetings",
        "description": "Calls, standups, calendars, and video conferencing sessions.",
        "color": CYAN,
    },
    "planning": {
        "label": "Planning",
        "description": "Task boards, backlog grooming, Kanban tools, and roadmaps.",
        "color": ORANGE,
    },
    "reading": {
        "label": "Reading",
        "description": "PDFs, e-books, long articles, and deliberate reading sessions.",
        "color": TEAL,
    },
}


DEFAULT_WARNING_CATEGORIES = ["entertainment", "browsing"]


def category_label(category: str) -> str:
    return CATEGORY_META.get(category, {}).get("label", str(category or "").title())


def category_description(category: str) -> str:
    return CATEGORY_META.get(category, {}).get("description", "")


def category_color(category: str) -> str:
    return CATEGORY_META.get(category, {}).get("color", ACCENT)


def all_focus_categories() -> list[str]:
    return list(CATEGORY_META.keys())


class _CategoryChip(QFrame):
    removed = pyqtSignal(str)

    def __init__(self, category: str, parent=None):
        super().__init__(parent)
        self.category = category
        color = category_color(category)
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {color}20;
                border: 1px solid {color}55;
                border-radius: 14px;
            }}
            """
        )

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 5, 6, 5)
        row.setSpacing(6)

        label = QLabel(category_label(category))
        label.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        label.setStyleSheet(f"color:{TEXT_PRIMARY}; background:transparent;")
        row.addWidget(label)

        remove_btn = QPushButton("x")
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setFixedSize(18, 18)
        remove_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_SECONDARY};
                border: none;
                border-radius: 9px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {BG_CARD_ALT};
                color: {TEXT_PRIMARY};
            }}
            """
        )
        remove_btn.clicked.connect(lambda: self.removed.emit(self.category))
        row.addWidget(remove_btn)


class CategoryTagSelector(QWidget):
    categories_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._categories: list[str] = []
        self._build()

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        self._box = QFrame()
        self._box.setStyleSheet(
            f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 12px;
            }}
            """
        )
        box_layout = QVBoxLayout(self._box)
        box_layout.setContentsMargins(12, 12, 12, 12)
        box_layout.setSpacing(8)

        self._placeholder = QLabel("No categories selected. Add the activities that should trigger attention alerts.")
        self._placeholder.setWordWrap(True)
        self._placeholder.setStyleSheet(f"color:{TEXT_MUTED}; background:transparent;")
        box_layout.addWidget(self._placeholder)

        self._tags_grid = QGridLayout()
        self._tags_grid.setContentsMargins(0, 0, 0, 0)
        self._tags_grid.setHorizontalSpacing(8)
        self._tags_grid.setVerticalSpacing(8)
        box_layout.addLayout(self._tags_grid)

        root.addWidget(self._box, stretch=1)

        self._add_btn = QPushButton("+ Add")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.setFixedHeight(36)
        self._add_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {ACCENT};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 0 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #4f46e5;
            }}
            """
        )
        self._add_btn.clicked.connect(self._show_menu)
        root.addWidget(self._add_btn, alignment=Qt.AlignmentFlag.AlignTop)

    def categories(self) -> list[str]:
        return list(self._categories)

    def set_categories(self, categories: list[str] | None, emit_signal: bool = False):
        normalized: list[str] = []
        for raw in categories or []:
            cat = str(raw).strip().lower()
            if cat and cat in CATEGORY_META and cat not in normalized:
                normalized.append(cat)
        self._categories = normalized
        self._refresh_tags()
        if emit_signal:
            self.categories_changed.emit(self.categories())

    def add_category(self, category: str):
        cat = str(category).strip().lower()
        if not cat or cat not in CATEGORY_META or cat in self._categories:
            return
        self._categories.append(cat)
        self._refresh_tags()
        self.categories_changed.emit(self.categories())

    def remove_category(self, category: str):
        cat = str(category).strip().lower()
        if cat not in self._categories:
            return
        self._categories = [item for item in self._categories if item != cat]
        self._refresh_tags()
        self.categories_changed.emit(self.categories())

    def _show_menu(self):
        menu = QMenu(self)
        for category in all_focus_categories():
            meta = CATEGORY_META[category]
            action = menu.addAction(f"{meta['label']}  -  {meta['description']}")
            action.setEnabled(category not in self._categories)
            action.triggered.connect(lambda checked=False, cat=category: self.add_category(cat))
        menu.exec(self._add_btn.mapToGlobal(self._add_btn.rect().bottomLeft()))

    def _clear_grid(self):
        while self._tags_grid.count():
            item = self._tags_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _refresh_tags(self):
        self._clear_grid()
        has_categories = bool(self._categories)
        self._placeholder.setVisible(not has_categories)

        for index, category in enumerate(self._categories):
            chip = _CategoryChip(category)
            chip.removed.connect(self.remove_category)
            row = index // 3
            col = index % 3
            self._tags_grid.addWidget(chip, row, col)
