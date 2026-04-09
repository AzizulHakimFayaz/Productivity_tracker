from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor


def apply_soft_shadow(
    widget: QWidget,
    blur_radius: int = 28,
    offset_y: int = 6,
    alpha: int = 72,
) -> None:
    """
    Apply a subtle shadow that improves card separation on dark backgrounds.
    """
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur_radius)
    shadow.setOffset(0, offset_y)
    shadow.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(shadow)
