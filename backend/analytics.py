import sqlite3
import datetime

from backend.database import PRODUCTIVE_CATEGORIES


class AnalyticsEngine:
    """Reads tracking data and provides insights to the UI."""
    def __init__(self, db_manager):
        self.db = db_manager

    def _get_start_timestamp(self, time_frame: str) -> float:
        now = datetime.datetime.now()
        if time_frame == "day":
            return now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        elif time_frame == "week":
            # Monday is 0, Sunday is 6. Start of current week.
            start_of_week = now - datetime.timedelta(days=min(now.weekday(), 6))
            return start_of_week.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        elif time_frame == "month":
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp()
        elif time_frame == "year":
            return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).timestamp()
        elif time_frame == "all":
            return 0.0
        return now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()

    def get_total_time(self, time_frame: str = "day") -> float:
        """Returns total active time for the given timeframe in seconds."""
        start_ts = self._get_start_timestamp(time_frame)
        
        self.db.cursor.execute('''
            SELECT SUM(duration) FROM activity_sessions 
            WHERE start_time >= ?
        ''', (start_ts,))
        
        res = self.db.cursor.fetchone()
        return res[0] if res and res[0] else 0.0

    def get_productive_time(self, time_frame: str = "day") -> float:
        """Returns productivity time counted only inside Focus Mode sessions."""
        start_ts = self._get_start_timestamp(time_frame)
        placeholders = ", ".join("?" for _ in PRODUCTIVE_CATEGORIES)
        self.db.cursor.execute(
            f'''
            SELECT COALESCE(SUM(duration), 0)
            FROM activity_sessions
            WHERE start_time >= ?
              AND is_focus_mode_session = 1
              AND category IN ({placeholders})
            ''',
            (start_ts, *PRODUCTIVE_CATEGORIES),
        )
        res = self.db.cursor.fetchone()
        return res[0] if res and res[0] else 0.0

    def get_focus_score(self, time_frame: str = "day") -> int:
        """
        Returns a 0-100 score based on how much of Focus Mode time landed in
        productive categories.
        """
        start_ts = self._get_start_timestamp(time_frame)
        self.db.cursor.execute(
            '''
            SELECT COALESCE(SUM(duration), 0)
            FROM activity_sessions
            WHERE start_time >= ?
              AND is_focus_mode_session = 1
            ''',
            (start_ts,),
        )
        res = self.db.cursor.fetchone()
        focus_secs = res[0] if res and res[0] else 0.0
        if focus_secs <= 0:
            return 0
        productive_secs = self.get_productive_time(time_frame)
        return int((productive_secs / focus_secs) * 100)

    def get_category_breakdown(self, time_frame: str = "day", focus_mode_only: bool = False) -> list:
        """Returns [(category, percentage, duration)]"""
        start_timestamp = self._get_start_timestamp(time_frame)
        params = [start_timestamp]
        focus_filter = ""
        if focus_mode_only:
            focus_filter = " AND is_focus_mode_session = 1"

        self.db.cursor.execute(f'''
            SELECT category, SUM(duration) as total_duration 
            FROM activity_sessions 
            WHERE start_time >= ? {focus_filter}
            GROUP BY category
            ORDER BY total_duration DESC
        ''', params)
        
        results = self.db.cursor.fetchall()
        total_time = sum([r[1] for r in results]) if results else 0
        
        breakdown = []
        for cat, dur in results:
            percentage = (dur / total_time * 100) if total_time > 0 else 0
            breakdown.append((cat, percentage, dur))
            
        return breakdown

    def get_app_usage(self, time_frame: str = "day") -> list:
        """Returns [(app_name_or_domain, percentage, duration)]"""
        start_timestamp = self._get_start_timestamp(time_frame)

        self.db.cursor.execute('''
            SELECT COALESCE(NULLIF(domain, ''), app) as target, SUM(duration) as total_duration 
            FROM activity_sessions 
            WHERE start_time >= ? AND category != 'Unknown' AND category != 'Idle'
            GROUP BY target
            ORDER BY total_duration DESC
        ''', (start_timestamp,))
        
        results = self.db.cursor.fetchall()
        total_time = sum([r[1] for r in results]) if results else 0
        
        usage = []
        for target, dur in results:
            percentage = (dur / total_time * 100) if total_time > 0 else 0
            # Clean up the output slightly
            clean_target = target.replace('.exe', '').title() if '.exe' in target else target
            usage.append((clean_target, percentage, dur))
            
        return usage

    def get_app_switches(self, time_frame: str = "day") -> int:
        """Returns the number of context switches (app changes) for the timeframe."""
        start_ts = self._get_start_timestamp(time_frame)
        self.db.cursor.execute('''
            SELECT COUNT(*) FROM activity_sessions 
            WHERE start_time >= ?
        ''', (start_ts,))
        res = self.db.cursor.fetchone()
        count = res[0] if res else 0
        return max(0, count - 1) if count > 0 else 0

    def get_idle_time(self, time_frame: str = "day") -> float:
        """Returns the total idle time for the timeframe in seconds."""
        start_ts = self._get_start_timestamp(time_frame)
        self.db.cursor.execute('''
            SELECT SUM(duration) FROM activity_sessions 
            WHERE start_time >= ? AND app = 'Idle'
        ''', (start_ts,))
        res = self.db.cursor.fetchone()
        return res[0] if res and res[0] else 0.0

    def get_timeline_data(self, time_frame: str = "day", focus_mode_only: bool = False) -> list:
        """Returns [{start: float_hour, end: float_hour, color: category_color, time_range, task, category, duration}]"""
        start_timestamp = self._get_start_timestamp(time_frame)
        params = [start_timestamp]
        focus_filter = ""
        if focus_mode_only:
            focus_filter = " AND is_focus_mode_session = 1"

        self.db.cursor.execute(f'''
            SELECT start_time, end_time, app, title, category, duration, is_focus_mode_session
            FROM activity_sessions 
            WHERE start_time >= ? {focus_filter}
            ORDER BY start_time ASC
        ''', params)
        
        results = self.db.cursor.fetchall()
        
        color_map = {
            "coding": "#3b82f6",     # ACCENT color in UI
            "learning": "#10b981",   # GREEN
            "writing": "#f59e0b",    # ORANGE
            "communication": "#8b5cf6", # ACCENT_PURPLE
            "entertainment": "#ef4444", # DANGER
            "designing": "#ec4899",  # PINK
            "browsing": "#64748b",   # SLATE
            "meetings": "#06b6d4",   # CYAN
            "planning": "#8b5cf6",   # PURPLE (reusing ACCENT_PURPLE for cohesive color scheme)
            "reading": "#14b8a6",    # TEAL
            "unknown": "#6e7681"     # TEXT_MUTED
        }
        
        timeline = []
        for st, et, app, title, cat, dur, is_focus_mode_session in results:
            st_dt = datetime.datetime.fromtimestamp(st)
            et_dt = datetime.datetime.fromtimestamp(et)
            
            st_hour = st_dt.hour + (st_dt.minute / 60) + (st_dt.second / 3600)
            et_hour = et_dt.hour + (et_dt.minute / 60) + (et_dt.second / 3600)
            
            # Formatted strings for UI rows
            t_range = f"{st_dt.strftime('%H:%M')} - {et_dt.strftime('%H:%M')}"
            dur_m = int(dur // 60)
            if dur_m > 60:
                h = dur_m // 60
                m = dur_m % 60
                dur_str = f"{h}h {m}m"
            else:
                dur_str = f"{max(1, dur_m)}m"
                
            task_name = title if title and title != "Unknown Title" else app
            if len(task_name) > 30:
                task_name = task_name[:27] + "..."
                
            timeline.append({
                "start": st_hour,
                "end": et_hour,
                "day_of_week": st_dt.weekday(),   # 0=Mon, 6=Sun
                "day_of_month": st_dt.day,
                "month": st_dt.month,
                "date": st_dt.date().isoformat(),
                "color": color_map.get(cat, color_map["unknown"]),
                "time_range": t_range,
                "task": task_name,
                "category": cat.title(),
                "duration": dur_str,
                "duration_seconds": float(dur or 0.0),
                "is_focus_mode_session": bool(is_focus_mode_session),
                "is_active": False # Set to active in UI if it's the very last one
            })
            
        return timeline
