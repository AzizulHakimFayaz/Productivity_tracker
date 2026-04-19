from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QDateTimeEdit, QComboBox, QSpinBox, QPushButton, QMessageBox
from PyQt6.QtCore import QDateTime, Qt
from styles.theme import BG_MAIN, TEXT_PRIMARY, TEXT_SECONDARY

def _glass_styles() -> str:
    return f"""
        QLineEdit, QTextEdit, QDateTimeEdit, QComboBox, QSpinBox {{
            background: #111d34;
            color:{TEXT_PRIMARY};
            border:1px solid #2b3b57;
            border-radius:10px;
            padding: 6px 8px;
        }}
        QLineEdit:focus, QTextEdit:focus, QDateTimeEdit:focus, QComboBox:focus, QSpinBox:focus {{
            border:1px solid #61d6ff;
        }}
    """

class CreateTaskDialog(QDialog):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Task")
        self._engine = engine
        self.setFixedSize(400, 360)
        self.setStyleSheet(f"background-color: {BG_MAIN}; color: {TEXT_PRIMARY};" + _glass_styles())
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setSpacing(10)
        
        lbl = QLabel("Task title")
        lbl.setStyleSheet(f"color:{TEXT_SECONDARY}; font-weight:bold;")
        v.addWidget(lbl)
        
        self.task_title = QLineEdit()
        self.task_title.setPlaceholderText("Task title (e.g., Prepare report)")
        v.addWidget(self.task_title)
        
        lbl_desc = QLabel("Description")
        lbl_desc.setStyleSheet(f"color:{TEXT_SECONDARY}; font-weight:bold;")
        v.addWidget(lbl_desc)
        
        self.task_desc = QTextEdit()
        self.task_desc.setPlaceholderText("Description / notes (optional)")
        self.task_desc.setFixedHeight(60)
        v.addWidget(self.task_desc)
        
        row = QHBoxLayout()
        self.task_due = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.task_due.setCalendarPopup(True)
        self.task_due.setDisplayFormat("dd MMM yyyy, hh:mm AP")
        self.task_priority = QComboBox()
        self.task_priority.addItems(["high", "medium", "low"])
        
        self.task_reminder = QSpinBox()
        self.task_reminder.setRange(1, 1440)
        self.task_reminder.setValue(30)
        self.task_reminder.setSuffix(" min early")
        
        row.addWidget(self.task_due)
        row.addWidget(self.task_priority)
        row.addWidget(self.task_reminder)
        v.addLayout(row)
        
        v.addStretch()
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.add_btn = QPushButton("Add Task")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #22d3aa;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 8px 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: #2ee6bc; }}
        """)
        self.add_btn.clicked.connect(self._add_task)
        btn_row.addWidget(self.add_btn)
        v.addLayout(btn_row)

    def _add_task(self):
        title = self.task_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Planner", "Please enter a task title.")
            return
        due_dt = self.task_due.dateTime().toPyDateTime()
        self._engine.db_manager.add_task(
            title=title,
            description=self.task_desc.toPlainText(),
            due_ts=due_dt.timestamp(),
            priority=self.task_priority.currentText(),
            remind_before_min=self.task_reminder.value(),
        )
        self.accept()
