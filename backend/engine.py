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
    settings_changed = pyqtSignal(dict)
    focus_prompt_triggered = pyqtSignal(str, str, str) # kind, title, message
    
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
        self._last_warning_sample_ts = 0.0
        self._snoozed_until_ts = 0.0
        self._focus_mode_started_ts = 0.0
        self._focus_mode_elapsed_secs = 0.0
        self._focus_mode_last_sample_ts = 0.0
        self._focus_mode_last_break_bucket = 0
        self._focus_mode_break_snoozed_until_ts = 0.0
        self._focus_mode_completion_sent = False
        self.settings = {}
        self._manual_rules: dict[str, str] = {}
        self._load_settings()

    def _default_settings(self) -> dict:
        return {
            "focus_mode_enabled": False,
            "focus_session_minutes": 90,
            "focus_break_reminders_enabled": True,
            "focus_break_interval_minutes": 30,
            "focus_break_duration_minutes": 5,
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
        self.sessions.focus_mode_provider = self._focus_mode_enabled

    def _resolve_category(self, app: str, title: str, domain: str) -> str:
        dom = (domain or "").lower()
        for pattern, cat in self._manual_rules.items():
            if pattern and pattern in dom:
                return cat
        return self.classifier.classify(app, title, domain)

    def get_settings(self) -> dict:
        payload = self.settings.copy()
        payload["manual_category_rules"] = self._manual_rules.copy()
        return payload

    def _focus_mode_enabled(self) -> bool:
        return bool(self.settings.get("focus_mode_enabled", False))

    def _focus_session_seconds(self) -> int:
        return int(self.settings.get("focus_session_minutes", 90)) * 60

    def _focus_break_interval_seconds(self) -> int:
        return int(self.settings.get("focus_break_interval_minutes", 30)) * 60

    def _focus_break_duration_seconds(self) -> int:
        return int(self.settings.get("focus_break_duration_minutes", 5)) * 60

    def _start_focus_mode_session(self, start_ts: float | None = None):
        now_ts = float(start_ts or time.time())
        self._focus_mode_started_ts = now_ts
        self._focus_mode_elapsed_secs = 0.0
        self._focus_mode_last_sample_ts = now_ts
        self._focus_mode_last_break_bucket = 0
        self._focus_mode_break_snoozed_until_ts = 0.0
        self._focus_mode_completion_sent = False
        self._snoozed_until_ts = 0.0
        for key in list(self._warning_streaks.keys()):
            self._warning_streaks[key] = 0.0

    def _stop_focus_mode_session(self, reset_elapsed: bool = True):
        self._focus_mode_started_ts = 0.0
        self._focus_mode_last_sample_ts = 0.0
        self._focus_mode_last_break_bucket = 0
        self._focus_mode_break_snoozed_until_ts = 0.0
        self._focus_mode_completion_sent = False
        if reset_elapsed:
            self._focus_mode_elapsed_secs = 0.0

    def _persist_session(self, session: dict | None, emit_update: bool = True):
        if not session:
            return
        self.db_manager.insert_session(
            start_time=session["start_time"],
            end_time=session["end_time"],
            app=session["app"],
            title=session["title"],
            domain=session["domain"],
            category=session["category"],
            duration=session["duration"],
            is_focus_mode_session=bool(session.get("is_focus_mode_session", False)),
        )
        if emit_update:
            self.data_updated.emit()

    def _rollover_active_session(self, timestamp: float):
        completed_session = self.sessions.split_active_session(timestamp)
        if completed_session:
            self._persist_session(completed_session)

    def get_focus_mode_state(self) -> dict:
        enabled = self._focus_mode_enabled()
        session_secs = self._focus_session_seconds()
        break_enabled = bool(self.settings.get("focus_break_reminders_enabled", True))
        break_interval_secs = self._focus_break_interval_seconds()
        break_duration_secs = self._focus_break_duration_seconds()
        elapsed_secs = max(0, int(self._focus_mode_elapsed_secs))
        remaining_secs = max(0, session_secs - elapsed_secs) if enabled else session_secs

        next_break_secs = 0
        if break_enabled and break_interval_secs > 0:
            if elapsed_secs <= 0:
                next_break_secs = break_interval_secs
            else:
                into_cycle = elapsed_secs % break_interval_secs
                next_break_secs = break_interval_secs if into_cycle == 0 else break_interval_secs - into_cycle

        progress_pct = 0
        if session_secs > 0 and enabled:
            progress_pct = max(0, min(100, int((elapsed_secs / session_secs) * 100)))

        active_session = self.sessions.active_session or {}
        return {
            "enabled": enabled,
            "focus_session_minutes": int(self.settings.get("focus_session_minutes", 90)),
            "break_reminders_enabled": break_enabled,
            "break_interval_minutes": int(self.settings.get("focus_break_interval_minutes", 30)),
            "break_duration_minutes": int(self.settings.get("focus_break_duration_minutes", 5)),
            "warning_categories": list(self.settings.get("warning_categories", ["entertainment", "browsing"])),
            "warning_threshold_minutes": int(self.settings.get("warning_threshold_minutes", 10)),
            "warning_cooldown_minutes": int(self.settings.get("warning_cooldown_minutes", 30)),
            "elapsed_secs": elapsed_secs,
            "remaining_secs": remaining_secs,
            "next_break_secs": next_break_secs,
            "progress_pct": progress_pct,
            "started_ts": self._focus_mode_started_ts,
            "active_title": str(active_session.get("title", "")),
            "active_category": str(active_session.get("category", "unknown")),
        }

    def update_settings(self, new_settings: dict):
        new_settings = new_settings or {}
        previous_focus_enabled = bool(self.settings.get("focus_mode_enabled", False))
        defaults = self._default_settings()
        updated = defaults.copy()
        updated.update(self.settings)
        updated.update(new_settings)

        # Guardrails for persisted values
        updated["focus_session_minutes"] = max(
            5,
            min(int(updated.get("focus_session_minutes", 90)), 480),
        )
        updated["focus_break_interval_minutes"] = max(
            10,
            min(int(updated.get("focus_break_interval_minutes", 30)), 180),
        )
        updated["focus_break_duration_minutes"] = max(
            1,
            min(int(updated.get("focus_break_duration_minutes", 5)), 60),
        )
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
        normalized_categories = []
        for raw in categories:
            cat = str(raw).strip().lower()
            if cat and cat not in normalized_categories:
                normalized_categories.append(cat)
        updated["warning_categories"] = normalized_categories

        self.settings = updated
        self._apply_runtime_settings()
        for key, value in updated.items():
            self.db_manager.set_setting(key, value)

        # Manual rules persisted separately (if provided in new_settings)
        manual_rules = new_settings.get("manual_category_rules")
        if isinstance(manual_rules, dict):
            self.db_manager.replace_manual_rules(manual_rules)
            self._manual_rules = {
                str(pattern).strip().lower(): str(category).strip().lower()
                for pattern, category in manual_rules.items()
                if str(pattern).strip()
            }

        current_focus_enabled = bool(updated.get("focus_mode_enabled", False))
        focus_mode_toggled = previous_focus_enabled != current_focus_enabled
        if focus_mode_toggled:
            self._rollover_active_session(time.time())

        if not previous_focus_enabled and current_focus_enabled:
            self._start_focus_mode_session(time.time())
        elif previous_focus_enabled and not current_focus_enabled:
            self._stop_focus_mode_session(reset_elapsed=True)

        self.settings_changed.emit(self.get_settings())

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

    def snooze_focus_breaks(self, minutes: int = 10):
        mins = max(1, int(minutes))
        self._focus_mode_break_snoozed_until_ts = time.time() + mins * 60

    def take_break_now_ack(self):
        self._focus_mode_break_snoozed_until_ts = time.time() + self._focus_break_duration_seconds()

    def focus_now_ack(self):
        """
        User acknowledged alert and wants to refocus now.
        Clears temporary mute and warning streak buffers.
        """
        self._snoozed_until_ts = 0.0
        for key in list(self._warning_streaks.keys()):
            self._warning_streaks[key] = 0.0

    def _check_warnings(self, category: str, duration: float):
        """Checks live distracting streaks against the configured warning categories."""
        if duration <= 0 or not self._focus_mode_enabled():
            return
        if self._is_in_quiet_hours():
            return
        if time.time() < self._snoozed_until_ts:
            return
            
        cat = str(category or "unknown").lower()
        categories = set(self.settings.get("warning_categories", ["entertainment", "browsing"]))
        threshold_secs = float(self.settings.get("warning_threshold_minutes", 10)) * 60.0
        cooldown_secs = float(self.settings.get("warning_cooldown_minutes", 30)) * 60.0

        if cat in categories:
            self._warning_streaks[cat] = self._warning_streaks.get(cat, 0.0) + duration
            for key in list(self._warning_streaks.keys()):
                if key != cat:
                    self._warning_streaks[key] = max(0.0, self._warning_streaks[key] - duration)
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

    def _update_live_warning_state(self, current_time: float, completed_session):
        if self._last_warning_sample_ts <= 0:
            self._last_warning_sample_ts = current_time
            return

        elapsed = max(0.0, current_time - self._last_warning_sample_ts)
        self._last_warning_sample_ts = current_time
        if elapsed <= 0:
            return

        segment_category = None
        if completed_session:
            segment_category = completed_session.get("category", "unknown")
        elif self.sessions.active_session:
            segment_category = self.sessions.active_session.get("category", "unknown")

        if segment_category:
            self._check_warnings(segment_category, elapsed)

    def _update_focus_mode_progress(self, current_time: float, idle_time: float):
        if not self._focus_mode_enabled():
            self._focus_mode_last_sample_ts = 0.0
            return

        if self._focus_mode_started_ts <= 0:
            self._start_focus_mode_session(current_time)
            return

        if self._focus_mode_last_sample_ts <= 0:
            self._focus_mode_last_sample_ts = current_time
            return

        elapsed = max(0.0, current_time - self._focus_mode_last_sample_ts)
        self._focus_mode_last_sample_ts = current_time
        if elapsed <= 0:
            return

        if idle_time <= self.tracker.idle_threshold:
            self._focus_mode_elapsed_secs += elapsed

        if (
            bool(self.settings.get("focus_break_reminders_enabled", True))
            and time.time() >= self._focus_mode_break_snoozed_until_ts
        ):
            break_interval_secs = self._focus_break_interval_seconds()
            if break_interval_secs > 0:
                current_bucket = int(self._focus_mode_elapsed_secs // break_interval_secs)
                if current_bucket > self._focus_mode_last_break_bucket:
                    self._focus_mode_last_break_bucket = current_bucket
                    if self._focus_mode_elapsed_secs < self._focus_session_seconds():
                        break_duration = int(self.settings.get("focus_break_duration_minutes", 5))
                        elapsed_minutes = max(1, int(self._focus_mode_elapsed_secs // 60))
                        self.focus_prompt_triggered.emit(
                            "break",
                            "Recovery break suggested",
                            (
                                f"You have been in Focus Mode for about {elapsed_minutes} minute(s). "
                                f"Stand up, stretch, and take a {break_duration}-minute reset."
                            ),
                        )

        if (
            self._focus_session_seconds() > 0
            and self._focus_mode_elapsed_secs >= self._focus_session_seconds()
            and not self._focus_mode_completion_sent
        ):
            self._focus_mode_completion_sent = True
            break_duration = int(self.settings.get("focus_break_duration_minutes", 5))
            session_minutes = int(self.settings.get("focus_session_minutes", 90))
            self.focus_prompt_triggered.emit(
                "complete",
                "Focus sprint complete",
                (
                    f"You completed your {session_minutes}-minute focus block. "
                    f"Take {break_duration} minute(s) away from the screen before the next sprint."
                ),
            )
            self.update_settings({"focus_mode_enabled": False})

    def run(self):
        """The main loop running in the background thread."""
        self._is_running = True
        self._last_warning_sample_ts = 0.0
        self._focus_mode_last_sample_ts = 0.0
        
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
                    self._update_focus_mode_progress(current_time, idle_time)
                    self._update_live_warning_state(current_time, completed_session)
                    
                    # Determine current live category
                    if self.sessions.active_session:
                        live_cat = self.sessions.active_session.get("category", "unknown")
                        if self.last_app != app or self.last_title != title:
                            self.current_activity_changed.emit(app, title, domain, live_cat)
                            self.last_app = app
                            self.last_title = title
                    
                    # 3. If a session just closed, save it
                    if completed_session:
                        self._persist_session(completed_session)
                        
            except Exception as e:
                print(f"Engine Loop Error: {e}")
                
            # Sleep until next check
            time.sleep(self.check_interval)
            
    def stop(self):
        """Cleanly stop the tracker."""
        self._is_running = False
        self._last_warning_sample_ts = 0.0
        self._focus_mode_last_sample_ts = 0.0
        self._stop_focus_mode_session(reset_elapsed=True)
        
        # Force final session to close and save
        if hasattr(self, 'sessions') and self.sessions:
            final_session = self.sessions.force_close_session(time.time())
            if final_session:
                self._persist_session(final_session, emit_update=False)
        self.wait()

    # --- Wrapper methods for Analytics ---
    def get_total_time(self, time_frame="day"):
        return self.analytics.get_total_time(time_frame)
        
    def get_productive_time(self, time_frame="day"):
        return self.analytics.get_productive_time(time_frame)

    def get_focus_score(self, time_frame="day"):
        return self.analytics.get_focus_score(time_frame)
        
    def get_category_breakdown(self, time_frame="day", focus_mode_only=False):
        return self.analytics.get_category_breakdown(time_frame, focus_mode_only=focus_mode_only)
        
    def get_app_usage(self, time_frame="day"):
        return self.analytics.get_app_usage(time_frame)
        
    def get_timeline_data(self, time_frame="day", focus_mode_only=False):
        return self.analytics.get_timeline_data(time_frame, focus_mode_only=focus_mode_only)

    def get_app_switches(self, time_frame="day"):
        return self.analytics.get_app_switches(time_frame)

    def get_idle_time(self, time_frame="day"):
        return self.analytics.get_idle_time(time_frame)
