import sys
import os
import time
import datetime

# Make sure project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Persistent model cache path for installed builds
_APPDATA = os.getenv("APPDATA")
if _APPDATA:
    _CACHE_ROOT = os.path.join(_APPDATA, "FocusIO", "model_cache")
    os.makedirs(_CACHE_ROOT, exist_ok=True)
    os.environ.setdefault("XDG_CACHE_HOME", _CACHE_ROOT)
    os.environ.setdefault("HF_HOME", _CACHE_ROOT)
    os.environ.setdefault("TRANSFORMERS_CACHE", _CACHE_ROOT)
    os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", _CACHE_ROOT)

# ── Pre-load ONNX / FastEmbed BEFORE PyQt6 ──────────────────────────────
# PyQt6 loads DLLs that conflict with ONNX runtime on Windows.
# By initializing the classifier first, ONNX loads cleanly.
from backend.classifier import ActivityClassifier
_preloaded_classifier = ActivityClassifier()

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QBrush
from PyQt6.QtCore import Qt, QTimer

from styles.theme import APP_STYLE, ACCENT
from ui.onboarding import OnboardingWindow


def _make_tray_icon() -> QIcon:
    """Build a simple coloured circle icon for the system tray."""
    px = QPixmap(32, 32)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(ACCENT)))
    p.drawEllipse(0, 0, 32, 32)
    p.setPen(QColor("white"))
    p.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
    p.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, "⚡")
    p.end()
    return QIcon(px)


def _setup_tray(app) -> QSystemTrayIcon:
    """Create a system tray icon so the app runs in the background."""
    tray = QSystemTrayIcon(_make_tray_icon(), app)
    tray.setToolTip("Focus.io — Productivity Tracker")

    menu = QMenu()

    show_act = menu.addAction("📊  Open Focus.io")
    def _show():
        if app.main_window:
            app.main_window.show()
            app.main_window.raise_()
            app.main_window.activateWindow()
    show_act.triggered.connect(_show)

    show_mini_act = menu.addAction("🕒  Show Mini Tracker")
    def _show_mini():
        if hasattr(app, 'mini_tracker') and app.mini_tracker:
            app.mini_tracker.show()
            app.mini_tracker.raise_()
            app.mini_tracker.activateWindow()
    show_mini_act.triggered.connect(_show_mini)

    menu.addSeparator()

    quit_act = menu.addAction("✕  Quit")
    def _quit():
        tray.hide()
        if hasattr(app, 'backend_engine'):
            try:
                app.backend_engine.stop()
            except Exception:
                pass
        if hasattr(app, 'mini_tracker'):
            try:
                app.mini_tracker.close()
            except Exception:
                pass
        app.quit()
    quit_act.triggered.connect(_quit)

    tray.setContextMenu(menu)

    # Double-click → show main window
    def _on_tray_activated(reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            _show()
    tray.activated.connect(_on_tray_activated)

    tray.show()
    return tray


def main():
    app = QApplication(sys.argv)

    # Keep running when all windows are closed (background mode)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(APP_STYLE)

    app.main_window    = None
    app.backend_engine = None
    app.mini_tracker   = None
    app.tray           = None
    app.task_notifier  = None
    app._daily_agenda_notified_on = None

    def _on_onboarding_done():
        from ui.main_window import MainWindow
        from backend.engine import TrackerEngine
        from ui.mini_tracker import MiniTrackerWidget

        app.main_window = MainWindow()

        # System tray — app lives here even when main window is hidden
        app.tray = _setup_tray(app)

        # Backend engine (reuse the pre-loaded classifier so ONNX works)
        app.backend_engine = TrackerEngine(classifier=_preloaded_classifier)
        app.main_window.set_engine(app.backend_engine)

        # Floating mini tracker
        app.mini_tracker = MiniTrackerWidget()
        app.mini_tracker.show()

        # ── Signals ───────────────────────────────────────────────────────────

        def on_activity(app_name, title, domain, cat):
            print(f"[TRACKER] Active: {app_name} | {domain} | {cat}")
            app.main_window._dash_page.active_card.update_session(app_name, title, cat)
            app.mini_tracker.update_activity(app_name, title, domain, cat)

        app.backend_engine.current_activity_changed.connect(on_activity)

        def on_data_updated():
            app.main_window._dash_page.refresh_data(app.backend_engine)
            app.main_window._analytics.refresh_data(app.backend_engine)

        app.backend_engine.data_updated.connect(on_data_updated)

        def on_warning(title, msg):
            """
            Full-screen attention overlay that forces itself in front of
            ANY window (YouTube, Chrome, games…) using Win32 ctypes calls.
            """
            from ui.attention_dialog import show_attention_dialog

            dlg = show_attention_dialog(
                task_name=title,
                warning_message=msg,
                on_snooze=lambda: app.backend_engine.snooze_alerts(10),
                on_resume=lambda: app.backend_engine.focus_now_ack(),
            )

            # Show the dialog first so it has a valid HWND
            dlg.show()
            dlg.raise_()
            dlg.activateWindow()

            # Windows: force the window to the absolute foreground
            try:
                import ctypes
                hwnd = int(dlg.winId())
                ctypes.windll.user32.ShowWindow(hwnd, 9)        # SW_RESTORE
                ctypes.windll.user32.BringWindowToTop(hwnd)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception:
                pass

            # Tray notification as extra nudge
            if app.tray:
                app.tray.showMessage(
                    "⚠ Attention Needed",
                    title,
                    QSystemTrayIcon.MessageIcon.Warning,
                    4000,
                )

            dlg.exec()   # block until user clicks Snooze / Focus Now

        app.backend_engine.warning_triggered.connect(on_warning)

        # ── Task notification loop (calendar/task system) ───────────────────
        def _notify(message_title: str, message_text: str, icon=QSystemTrayIcon.MessageIcon.Information):
            if app.tray:
                app.tray.showMessage(message_title, message_text, icon, 5000)

        def _check_task_notifications():
            if not app.backend_engine:
                return
            now_ts = time.time()
            db = app.backend_engine.db_manager

            # 1) Upcoming reminders (before deadline)
            upcoming = db.get_upcoming_task_notifications(now_ts)
            for task in upcoming:
                due_dt = datetime.datetime.fromtimestamp(task["due_ts"]).strftime("%I:%M %p").lstrip("0")
                _notify(
                    "⏰ Task Reminder",
                    f"'{task['title']}' is due at {due_dt}.",
                    QSystemTrayIcon.MessageIcon.Warning,
                )
                db.mark_task_notified(task["id"], "upcoming")

            # 2) Overdue reminders
            overdue = db.get_overdue_task_notifications(now_ts)
            for task in overdue:
                _notify(
                    "⚠ Task Overdue",
                    f"'{task['title']}' is overdue. Open Planner to update it.",
                    QSystemTrayIcon.MessageIcon.Warning,
                )
                db.mark_task_notified(task["id"], "overdue")

            # 3) Daily agenda nudge (once per day)
            today = datetime.date.today().isoformat()
            if app._daily_agenda_notified_on != today:
                due_today = db.get_tasks_due_on_date(datetime.date.today())
                pending_today = [t for t in due_today if t["status"] == "pending"]
                if pending_today:
                    _notify(
                        "📅 Daily Agenda",
                        f"You have {len(pending_today)} task(s) due today.",
                        QSystemTrayIcon.MessageIcon.Information,
                    )
                app._daily_agenda_notified_on = today

        app.task_notifier = QTimer()
        app.task_notifier.timeout.connect(_check_task_notifications)
        app.task_notifier.start(60_000)  # every minute
        _check_task_notifications()

        # ── Quit cleanup ──────────────────────────────────────────────────────
        def _on_quit():
            if app.tray:
                app.tray.hide()
            if app.backend_engine:
                try:
                    app.backend_engine.stop()
                except Exception:
                    pass
            if app.mini_tracker:
                try:
                    app.mini_tracker.close()
                except Exception:
                    pass
            if app.task_notifier:
                app.task_notifier.stop()

        app.aboutToQuit.connect(_on_quit)

        app.backend_engine.start()
        app.main_window.show()
        onboarding.hide()

    onboarding = OnboardingWindow()
    onboarding._finish_onboarding = _on_onboarding_done
    onboarding._cat.on_continue = _on_onboarding_done
    onboarding.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
