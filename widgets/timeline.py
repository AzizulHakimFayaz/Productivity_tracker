import datetime
from PyQt6.QtWidgets import QWidget, QScrollArea, QVBoxLayout
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPainterPath, QCursor
from PyQt6.QtCore import Qt, QRectF, pyqtSignal

from styles.theme import BG_CARD_ALT, BORDER, TEXT_MUTED, TEXT_PRIMARY

class TimelinePainter(QWidget):
    sessionClicked = pyqtSignal(dict)
    hourClicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(1440)  # 24 hours * 60 pixels per hour
        self.sessions = []
        self._hitboxes = []
        # Margins
        self.LEFT_MARGIN = 75
        self.HOUR_HEIGHT = 60
        self._hover_y = None
        self._hover_margin_hour = None
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_sessions(self, sessions):
        self.sessions = sessions or []
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # 1. Draw Grid Lines and Labels
        font_time = QFont("Segoe UI", 9)
        painter.setFont(font_time)
        painter.setPen(QColor(TEXT_MUTED))

        grid_pen = QPen(QColor(BORDER))
        grid_pen.setWidth(1)

        for hour in range(30): # Draw past 24 for scroll safety
            y = int(hour * self.HOUR_HEIGHT)
            
            # Text formatting
            if hour % 24 == 0:
                label = "12 AM"
            elif hour % 24 == 12:
                label = "12 PM"
            elif hour % 24 < 12:
                label = f"{hour % 24} AM"
            else:
                label = f"{(hour % 24) - 12} PM"

            # Draw time label
            painter.setPen(QColor(TEXT_MUTED))
            painter.drawText(
                QRectF(0, y - 8, self.LEFT_MARGIN - 10, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label
            )

            # Draw horizontal grid line
            painter.setPen(grid_pen)
            painter.drawLine(int(self.LEFT_MARGIN), y, int(width), y)

        if hasattr(self, '_hover_margin_hour') and self._hover_margin_hour is not None and 0 <= self._hover_margin_hour < 30:
            btn_y = self._hover_margin_hour * self.HOUR_HEIGHT + (self.HOUR_HEIGHT - 22) / 2
            brect = QRectF(self.LEFT_MARGIN - 58, btn_y, 48, 22)
            path = QPainterPath()
            path.addRoundedRect(brect, 6, 6)
            painter.fillPath(path, QColor(43, 59, 87, 200))
            painter.setPen(QColor("#a8b8d8"))
            painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            painter.drawText(brect, Qt.AlignmentFlag.AlignCenter, "🔍 Apps")

        # 2. Draw Activity Blocks
        self._hitboxes.clear()
        for s in self.sessions:
            start_ts = s.get("start_time")
            end_ts = s.get("end_time")
            if not start_ts or not end_ts:
                continue
            
            dt_start = datetime.datetime.fromtimestamp(start_ts)
            duration_minutes = max(1, s.get("duration", 0) / 60)
            
            start_minutes = dt_start.hour * 60 + dt_start.minute
            y1 = start_minutes * (self.HOUR_HEIGHT / 60)
            h = duration_minutes * (self.HOUR_HEIGHT / 60)
            
            x = self.LEFT_MARGIN + 2
            w = width - self.LEFT_MARGIN - 12
            
            cat = str(s.get("category", "")).title()
            # Assign colors
            if cat in ["Coding", "Learning", "Writing"]:
                bg_color = QColor(47, 214, 180, 200) # Cyan/Teal
                border_color = QColor(47, 214, 180, 255)
                text_color = QColor("#0d1d29")
            elif cat in ["Entertainment", "Browsing"]:
                bg_color = QColor(139, 92, 246, 200) # Purple
                border_color = QColor(139, 92, 246, 255)
                text_color = QColor("white")
            else:
                bg_color = QColor(59, 130, 246, 200) # Blue
                border_color = QColor(59, 130, 246, 255)
                text_color = QColor("white")

            rect = QRectF(x, y1, w, h)
            self._hitboxes.append((rect, s))
            
            # Draw rounded block
            path = QPainterPath()
            path.addRoundedRect(rect, 4, 4)
            painter.fillPath(path, bg_color)
            painter.setPen(QPen(border_color, 1))
            painter.drawPath(path)

            # Draw text if height is large enough
            if h >= 14:
                painter.setPen(text_color)
                font_block = QFont("Segoe UI", 8, QFont.Weight.Bold)
                painter.setFont(font_block)
                
                title = s.get("title") or s.get("app") or "Unknown"
                if "youtube" in str(s.get("app", "")).lower():
                    title = "YouTube: " + title
                
                # Simple clipping based on block width/height
                text_rect = rect.adjusted(4, 2, -4, -2)
                painter.drawText(
                    text_rect,
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                    title
                )

        # 3. Draw Hover Line
        if hasattr(self, '_hover_y') and self._hover_y is not None and 0 <= self._hover_y <= height:
            total_minutes = self._hover_y * (60 / self.HOUR_HEIGHT)
            hour = int(total_minutes // 60)
            minute = int(total_minutes % 60)
            
            period = "AM"
            display_hour = hour
            if hour >= 12:
                period = "PM"
                if hour > 12:
                    display_hour -= 12
            if display_hour == 0:
                display_hour = 12
            
            time_str = f"{display_hour}:{minute:02d} {period}"
            
            painter.setPen(QPen(QColor("#a8b8d8"), 1))
            painter.drawLine(int(self.LEFT_MARGIN), int(self._hover_y), int(width), int(self._hover_y))
            
            font_hover = QFont("Segoe UI", 8, QFont.Weight.Medium)
            painter.setFont(font_hover)
            text_width = painter.fontMetrics().horizontalAdvance(time_str)
            box_width = text_width + 12
            box_height = 20
            
            box_x = self.LEFT_MARGIN - box_width - 6
            # Clamp pill so it doesn't clip top/bottom
            box_y = max(0, min(self._hover_y - box_height / 2, height - box_height))
            
            pill_rect = QRectF(box_x, box_y, box_width, box_height)
            
            path = QPainterPath()
            path.addRoundedRect(pill_rect, 4, 4)
            painter.fillPath(path, QColor("#1e293b"))
            painter.setPen(QPen(QColor("#334155"), 1))
            painter.drawPath(path)
            
            painter.setPen(QColor("#7dd3fc"))
            painter.drawText(
                pill_rect,
                Qt.AlignmentFlag.AlignCenter,
                time_str
            )

    def mousePressEvent(self, event):
        pos = event.position()
        if pos.x() < self.LEFT_MARGIN:
            hour = int(pos.y() // self.HOUR_HEIGHT)
            self.hourClicked.emit(hour)
            super().mousePressEvent(event)
            return

        for rect, s in self._hitboxes:
            if rect.contains(pos):
                self.sessionClicked.emit(s)
                break
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.position()
        self._hover_y = pos.y()
        if pos.x() < self.LEFT_MARGIN:
            self._hover_margin_hour = int(pos.y() // self.HOUR_HEIGHT)
        else:
            self._hover_margin_hour = None
        self.update()

    def leaveEvent(self, event):
        self._hover_y = None
        self._hover_margin_hour = None
        self.update()
        super().leaveEvent(event)

class TimelineWidget(QScrollArea):
    sessionClicked = pyqtSignal(dict)
    hourClicked = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setStyleSheet(f"""
            QScrollArea {{
                background: {BG_CARD_ALT};
                border: 1px solid {BORDER};
                border-radius: 12px;
            }}
            QScrollBar:vertical {{
                border: none;
                background: #0f1930;
                width: 10px;
                margin: 0px 0px 0px 0px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: #2a3a56;
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        self.painter = TimelinePainter()
        self.painter.sessionClicked.connect(self.sessionClicked.emit)
        self.painter.hourClicked.connect(self.hourClicked.emit)
        
        # Wrapping in a background widget
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        v = QVBoxLayout(self.container)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(self.painter)
        
        self.setWidget(self.container)

    def set_sessions(self, sessions, start_ts=None, end_ts=None):
        # We can also filter sessions to only exactly what belongs to the day if needed.
        # But the parent query handles this.
        self.painter.set_sessions(sessions)
        
        # Scroll to first event, or to current time if empty
        if sessions:
            first_ev = min(sessions, key=lambda x: x.get("start_time", 0))
            dt = datetime.datetime.fromtimestamp(first_ev.get("start_time"))
            y = (dt.hour * 60 + dt.minute) * (self.painter.HOUR_HEIGHT / 60)
            self.verticalScrollBar().setValue(int(max(0, y - 50)))
        else:
            now = datetime.datetime.now()
            y = (now.hour * 60) * (self.painter.HOUR_HEIGHT / 60)
            self.verticalScrollBar().setValue(int(max(0, y - 100)))

