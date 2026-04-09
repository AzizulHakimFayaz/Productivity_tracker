import time
import datetime
from PyQt6.QtCore import QThread, pyqtSignal

from backend.database import DatabaseManager
from backend.analytics import AnalyticsEngine
from backend.tracker import ActivityTracker
from backend.classifier import ActivityClassifier
from backend.sessions import SessionManager

class TrackerEngine(QThread):
    """
    Main background thread that runs the tracking loop.
    Emits data to the PyQt UI without blocking.
    """
    
    # Signals for UI Integration
    data_updated = pyqtSignal() # Emitted when a session is finalized and saved
    warning_triggered = pyqtSignal(str, str) # title, message for warnings (e.g. entertainment > 15m)
    current_activity_changed = pyqtSignal(str, str, str, str) # app, title, domain, category
    
    def __init__(self, check_interval=3.0, classifier=None, parent=None):
        super().__init__(parent)
        self.check_interval = check_interval
        self._is_running = False
        
        # Initialize Backend Components
        self.db_manager = DatabaseManager()
        self.analytics = AnalyticsEngine(self.db_manager)
        
        self.tracker = ActivityTracker(idle_threshold=300)
        self.classifier = classifier or ActivityClassifier()
        self.sessions = SessionManager(self.classifier, idle_threshold=300)
        
        # State for Warnings
        self.entertainment_streak = 0.0
        self.last_app = None
        self.last_title = None
        self._warning_streaks: dict[str, float] = {}
        self._snoozed_until_ts = 0.0
        self.settings = {}
        self._manual_rules: dict[str, str] = {}
        self._load_settings()

    def _default_settings(self) -> dict:
        return {
            "alerts_enabled": True,
            "warning_categories": ["entertainment", "browsing"],
            "warning_threshold_minutes": 10,
            "warning_cooldown_minutes": 30,
            "idle_threshold_seconds": 300,
            "quiet_hours_enabled": False,
            "quiet_start_hour": 22,
            "quiet_end_hour": 7,
        }

    def _load_settings(self):
        defaults = self._default_settings()
        saved = self.db_manager.get_all_settings()
        merged = defaults.copy()
        merged.update(saved)
        self.settings = merged
        self._apply_runtime_settings()

    def _apply_runtime_settings(self):
        idle_threshold = int(self.settings.get("idle_threshold_seconds", 300))
        idle_threshold = max(30, min(idle_threshold, 3600))
        self.tracker.idle_threshold = idle_threshold
        self.sessions.idle_threshold = idle_threshold

        # Manual rules for domains (simple substring match)
        manual = self.db_manager.get_manual_rules()
        self._manual_rules = manual or {}
        # Ensure session manager uses resolver that respects rules
        self.sessions.category_resolver = self._resolve_category

    def _resolve_category(self, app: str, title: str, domain: str) -> str:
        dom = (domain or "").lower()
        for pattern, cat in self._manual_rules.items():
            if pattern and pattern in dom:
                return cat
        return self.classifier.classify(app, title, domain)

    def get_settings(self) -> dict:
        return self.settings.copy()

    def update_settings(self, new_settings: dict):
        defaults = self._default_settings()
        updated = defaults.copy()
        updated.update(self.settings)
        updated.update(new_settings or {})

        # Guardrails for persisted values
        updated["warning_threshold_minutes"] = max(
            1,
            min(int(updated.get("warning_threshold_minutes", 10)), 240),
        )
        updated["warning_cooldown_minutes"] = max(
            1,
            min(int(updated.get("warning_cooldown_minutes", 30)), 720),
        )
        updated["idle_threshold_seconds"] = max(
            30,
            min(int(updated.get("idle_threshold_seconds", 300)), 3600),
        )
        updated["quiet_start_hour"] = max(0, min(int(updated.get("quiet_start_hour", 22)), 23))
        updated["quiet_end_hour"] = max(0, min(int(updated.get("quiet_end_hour", 7)), 23))
        categories = updated.get("warning_categories", ["entertainment", "browsing"])
        if not isinstance(categories, list):
            categories = ["entertainment", "browsing"]
        updated["warning_categories"] = [str(c).lower() for c in categories]

        self.settings = updated
        self._apply_runtime_settings()
        for key, value in updated.items():
            self.db_manager.set_setting(key, value)

        # Manual rules persisted separately (if provided in new_settings)
        manual_rules = new_settings.get("manual_category_rules")
        if isinstance(manual_rules, dict):
            self.db_manager.replace_manual_rules(manual_rules)

    def _is_in_quiet_hours(self) -> bool:
        if not bool(self.settings.get("quiet_hours_enabled", False)):
            return False
        start_h = int(self.settings.get("quiet_start_hour", 22))
        end_h = int(self.settings.get("quiet_end_hour", 7))
        now_h = datetime.datetime.now().hour
        if start_h == end_h:
            return True
        if start_h < end_h:
            return start_h <= now_h < end_h
        return now_h >= start_h or now_h < end_h

    def snooze_alerts(self, minutes: int = 10):
        """
        Temporarily suppress attention warnings.
        """
        mins = max(1, int(minutes))
        self._snoozed_until_ts = time.time() + mins * 60

    def focus_now_ack(self):
        """
        User acknowledged alert and wants to refocus now.
        Clears temporary mute and warning streak buffers.
        """
        self._snoozed_until_ts = 0.0
        for key in list(self._warning_streaks.keys()):
            self._warning_streaks[key] = 0.0

    def _check_warnings(self, session):
        """Checks for context switches, long entertainment use, etc."""
        if not session or not bool(self.settings.get("alerts_enabled", True)):
            return
        if self._is_in_quiet_hours():
            return
        if time.time() < self._snoozed_until_ts:
            return
            
        cat = str(session.get("category", "unknown")).lower()
        duration = session.get("duration", 0)
        categories = set(self.settings.get("warning_categories", ["entertainment", "browsing"]))
        threshold_secs = float(self.settings.get("warning_threshold_minutes", 10)) * 60.0
        cooldown_secs = float(self.settings.get("warning_cooldown_minutes", 30)) * 60.0

        if cat in categories:
            self._warning_streaks[cat] = self._warning_streaks.get(cat, 0.0) + duration
            if self._warning_streaks[cat] >= threshold_secs:
                mins = int(self._warning_streaks[cat] // 60)
                self.warning_triggered.emit(
                    f"Attention: {cat.title()} drift",
                    (
                        f"You have spent about {mins} minutes on {cat}. "
                        "Consider switching back to your focus task."
                    ),
                )
                # cooldown by resetting to a negative buffer
                self._warning_streaks[cat] = -cooldown_secs
        else:
            # Decay non-relevant streaks gradually to prevent stale warnings.
            for key in list(self._warning_streaks.keys()):
                self._warning_streaks[key] = max(0.0, self._warning_streaks[key] - duration)

    def run(self):
        """The main loop running in the background thread."""
        self._is_running = True
        
        # Cleanup old database entries (retain 1 year history)
        self.db_manager.cleanup_old_data()
        
        while self._is_running:
            try:
                # 1. Grab current state
                state = self.tracker.get_current_state()
                if state:
                    app, title, domain, idle_time = state
                    current_time = time.time()
                    
                    # 2. Process Session Update
                    completed_session = self.sessions.process_activity(app, title, domain, current_time, idle_time)
                    
                    # Determine current live category
                    if self.sessions.active_session:
                        live_cat = self.sessions.active_session.get("category", "unknown")
                        if self.last_app != app or self.last_title != title:
                            self.current_activity_changed.emit(app, title, domain, live_cat)
                            self.last_app = app
                            self.last_title = title
                    
                    # 3. If a session just closed, save it
                    if completed_session:
                        self.db_manager.insert_session(
                            start_time=completed_session["start_time"],
                            end_time=completed_session["end_time"],
                            app=completed_session["app"],
                            title=completed_session["title"],
                            domain=completed_session["domain"],
                            category=completed_session["category"],
                            duration=completed_session["duration"]
                        )
                        
                        # Trigger warnings if necessary
                        self._check_warnings(completed_session)
                        
                        # Notify UI to refresh charts/stats
                        self.data_updated.emit()
                        
            except Exception as e:
                print(f"Engine Loop Error: {e}")
                
            # Sleep until next check
            time.sleep(self.check_interval)
            
    def stop(self):
        """Cleanly stop the tracker."""
        self._is_running = False
        
        # Force final session to close and save
        if hasattr(self, 'sessions') and self.sessions:
            final_session = self.sessions.force_close_session(time.time())
            if final_session:
                self.db_manager.insert_session(
                    start_time=final_session["start_time"],
                    end_time=final_session["end_time"],
                    app=final_session["app"],
                    title=final_session["title"],
                    domain=final_session["domain"],
                    category=final_session["category"],
                    duration=final_session["duration"]
                )
        self.wait()

    # --- Wrapper methods for Analytics ---
    def get_total_time(self, time_frame="day"):
        return self.analytics.get_total_time(time_frame)
        
    def get_category_breakdown(self, time_frame="day"):
        return self.analytics.get_category_breakdown(time_frame)
        
    def get_app_usage(self, time_frame="day"):
        return self.analytics.get_app_usage(time_frame)
        
    def get_timeline_data(self, time_frame="day"):
        return self.analytics.get_timeline_data(time_frame)

    def get_app_switches(self, time_frame="day"):
        return self.analytics.get_app_switches(time_frame)

    def get_idle_time(self, time_frame="day"):
        return self.analytics.get_idle_time(time_frame)
