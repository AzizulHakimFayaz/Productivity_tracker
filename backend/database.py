import sqlite3
import os
import datetime
import json
import shutil
import sys

def _get_data_dir() -> str:
    """
    Use a user-writable directory so installed builds work without admin rights.
    """
    appdata = os.getenv("APPDATA")
    if appdata:
        path = os.path.join(appdata, "FocusIO")
    else:
        path = os.path.join(os.path.dirname(__file__), ".focusio_data")
    os.makedirs(path, exist_ok=True)
    return path


DB_FILE = os.path.join(_get_data_dir(), "tracking.db")


def _legacy_db_candidates() -> list[str]:
    """
    Potential old database locations used before APPDATA migration.
    """
    candidates: list[str] = []

    # Old behavior: DB in current working directory.
    candidates.append(os.path.join(os.getcwd(), "tracking.db"))

    # Source-tree run: repo root (one level above backend).
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(os.path.dirname(backend_dir), "tracking.db"))

    # Frozen app run: next to executable.
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        candidates.append(os.path.join(exe_dir, "tracking.db"))

    # Deduplicate while preserving order.
    seen = set()
    ordered = []
    for p in candidates:
        ap = os.path.abspath(p)
        if ap not in seen:
            seen.add(ap)
            ordered.append(ap)
    return ordered


def _looks_like_focusio_db(path: str) -> bool:
    """
    Basic validation so we only migrate compatible DB files.
    """
    if not os.path.exists(path) or os.path.getsize(path) <= 0:
        return False
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='activity_sessions'"
        )
        ok = cur.fetchone() is not None
        conn.close()
        return ok
    except Exception:
        return False


def _seed_db_from_legacy_if_needed():
    """
    If APPDATA DB is missing/empty, try copying a legacy DB once.
    """
    should_seed = True
    try:
        if os.path.exists(DB_FILE) and os.path.getsize(DB_FILE) > 0:
            # If DB already has tracked sessions, do not replace it.
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='activity_sessions'"
            )
            has_table = cur.fetchone() is not None
            if has_table:
                cur.execute("SELECT COUNT(*) FROM activity_sessions")
                session_count = int(cur.fetchone()[0] or 0)
                should_seed = session_count == 0
            else:
                should_seed = True
            conn.close()
    except Exception:
        should_seed = True

    if not should_seed:
        return

    for src in _legacy_db_candidates():
        if os.path.abspath(src) == os.path.abspath(DB_FILE):
            continue
        if not _looks_like_focusio_db(src):
            continue
        try:
            shutil.copy2(src, DB_FILE)
            return
        except Exception:
            continue


_seed_db_from_legacy_if_needed()

class DatabaseManager:
    """Manages the SQLite database for productivity tracking."""
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        """Creates tables if they don't exist."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                app TEXT NOT NULL,
                title TEXT,
                domain TEXT,
                category TEXT NOT NULL,
                duration REAL NOT NULL
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                total_duration REAL DEFAULT 0,
                coding REAL DEFAULT 0,
                learning REAL DEFAULT 0,
                writing REAL DEFAULT 0,
                communication REAL DEFAULT 0,
                entertainment REAL DEFAULT 0,
                designing REAL DEFAULT 0,
                browsing REAL DEFAULT 0,
                meetings REAL DEFAULT 0,
                planning REAL DEFAULT 0,
                reading REAL DEFAULT 0
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS manual_category_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT NOT NULL,
                category TEXT NOT NULL
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                due_ts REAL NOT NULL,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'pending',
                remind_before_min INTEGER DEFAULT 30,
                reminder_sent INTEGER DEFAULT 0,
                overdue_sent INTEGER DEFAULT 0,
                created_ts REAL NOT NULL,
                completed_ts REAL
            )
        ''')
        
        # Migration: Add new columns if the table already existed from v1
        for col in ["designing", "browsing", "meetings", "planning", "reading"]:
            try:
                self.cursor.execute(f"ALTER TABLE daily_stats ADD COLUMN {col} REAL DEFAULT 0")
            except sqlite3.OperationalError:
                pass # Column exists

        # Creating index to speed up time-based queries
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_times ON activity_sessions(start_time, end_time)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_ts, status)')
        self.conn.commit()

    def get_setting(self, key: str, default=None):
        self.cursor.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            (key,),
        )
        row = self.cursor.fetchone()
        if not row:
            return default
        try:
            return json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            return default

    def set_setting(self, key: str, value):
        encoded = json.dumps(value)
        self.cursor.execute(
            '''
            INSERT INTO app_settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            ''',
            (key, encoded),
        )
        self.conn.commit()

    def get_all_settings(self) -> dict:
        self.cursor.execute("SELECT key, value FROM app_settings")
        data = {}
        for key, raw_value in self.cursor.fetchall():
            try:
                data[key] = json.loads(raw_value)
            except (json.JSONDecodeError, TypeError):
                continue
        return data

    # Manual category rules -------------------------------------------------
    def get_manual_rules(self) -> dict:
        """
        Returns {pattern: category}
        """
        self.cursor.execute("SELECT pattern, category FROM manual_category_rules")
        rules = {}
        for pattern, cat in self.cursor.fetchall():
            rules[str(pattern).strip().lower()] = str(cat).strip().lower()
        return rules

    def replace_manual_rules(self, rules: dict):
        """
        Replace all manual rules with the provided mapping.
        """
        self.cursor.execute("DELETE FROM manual_category_rules")
        for pattern, cat in (rules or {}).items():
            self.cursor.execute(
                "INSERT INTO manual_category_rules (pattern, category) VALUES (?, ?)",
                (str(pattern).strip(), str(cat).strip().lower()),
            )
        self.conn.commit()

    def export_database_copy(self, target_path: str):
        """
        Export the entire SQLite database to a new file.
        """
        dest = sqlite3.connect(target_path)
        with dest:
            self.conn.backup(dest)
        dest.close()

    def export_as_json(self, target_path: str):
        """
        Export all tracked data as JSON text so users can read it easily.
        Structure:
        {
          "activity_sessions": [...],
          "daily_stats": [...],
          "settings": {...},
          "manual_rules": {...}
        }
        """
        export = {}

        # Sessions
        self.cursor.execute(
            "SELECT id, start_time, end_time, app, title, domain, category, duration "
            "FROM activity_sessions ORDER BY start_time ASC"
        )
        cols = ["id", "start_time", "end_time", "app", "title", "domain", "category", "duration"]
        export["activity_sessions"] = [
            dict(zip(cols, row)) for row in self.cursor.fetchall()
        ]

        # Daily stats
        self.cursor.execute("PRAGMA table_info(daily_stats)")
        stat_cols = [c[1] for c in self.cursor.fetchall()]
        self.cursor.execute("SELECT * FROM daily_stats ORDER BY date ASC")
        export["daily_stats"] = [
            dict(zip(stat_cols, row)) for row in self.cursor.fetchall()
        ]

        # Settings and manual rules
        export["settings"] = self.get_all_settings()
        export["manual_rules"] = self.get_manual_rules()

        # Tasks
        export["tasks"] = self.get_tasks()

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(export, f, indent=2, ensure_ascii=False)

    # Tasks -----------------------------------------------------------------
    def add_task(
        self,
        title: str,
        description: str,
        due_ts: float,
        priority: str = "medium",
        remind_before_min: int = 30,
    ):
        now_ts = datetime.datetime.now().timestamp()
        self.cursor.execute(
            '''
            INSERT INTO tasks (
                title, description, due_ts, priority, status, remind_before_min,
                reminder_sent, overdue_sent, created_ts, completed_ts
            )
            VALUES (?, ?, ?, ?, 'pending', ?, 0, 0, ?, NULL)
            ''',
            (
                title.strip(),
                (description or "").strip(),
                float(due_ts),
                (priority or "medium").strip().lower(),
                int(remind_before_min),
                now_ts,
            ),
        )
        self.conn.commit()

    def get_tasks(self, status: str | None = None) -> list[dict]:
        base = (
            "SELECT id, title, description, due_ts, priority, status, "
            "remind_before_min, reminder_sent, overdue_sent, created_ts, completed_ts "
            "FROM tasks"
        )
        args = []
        if status:
            base += " WHERE status = ?"
            args.append(status)
        base += " ORDER BY due_ts ASC"
        self.cursor.execute(base, tuple(args))
        cols = [
            "id", "title", "description", "due_ts", "priority", "status",
            "remind_before_min", "reminder_sent", "overdue_sent", "created_ts", "completed_ts",
        ]
        return [dict(zip(cols, row)) for row in self.cursor.fetchall()]

    def update_task_status(self, task_id: int, status: str):
        status = status.strip().lower()
        completed_ts = datetime.datetime.now().timestamp() if status == "done" else None
        self.cursor.execute(
            '''
            UPDATE tasks
            SET status = ?, completed_ts = ?, reminder_sent = 0, overdue_sent = 0
            WHERE id = ?
            ''',
            (status, completed_ts, int(task_id)),
        )
        self.conn.commit()

    def delete_task(self, task_id: int):
        self.cursor.execute("DELETE FROM tasks WHERE id = ?", (int(task_id),))
        self.conn.commit()

    def get_upcoming_task_notifications(self, now_ts: float) -> list[dict]:
        self.cursor.execute(
            '''
            SELECT id, title, due_ts, remind_before_min
            FROM tasks
            WHERE status = 'pending'
              AND reminder_sent = 0
              AND due_ts > ?
              AND due_ts <= (? + remind_before_min * 60)
            ORDER BY due_ts ASC
            ''',
            (float(now_ts), float(now_ts)),
        )
        cols = ["id", "title", "due_ts", "remind_before_min"]
        return [dict(zip(cols, row)) for row in self.cursor.fetchall()]

    def get_overdue_task_notifications(self, now_ts: float) -> list[dict]:
        self.cursor.execute(
            '''
            SELECT id, title, due_ts
            FROM tasks
            WHERE status = 'pending'
              AND overdue_sent = 0
              AND due_ts <= ?
            ORDER BY due_ts ASC
            ''',
            (float(now_ts),),
        )
        cols = ["id", "title", "due_ts"]
        return [dict(zip(cols, row)) for row in self.cursor.fetchall()]

    def mark_task_notified(self, task_id: int, kind: str):
        if kind == "upcoming":
            self.cursor.execute(
                "UPDATE tasks SET reminder_sent = 1 WHERE id = ?",
                (int(task_id),),
            )
        elif kind == "overdue":
            self.cursor.execute(
                "UPDATE tasks SET overdue_sent = 1 WHERE id = ?",
                (int(task_id),),
            )
        self.conn.commit()

    def get_tasks_due_on_date(self, date_obj: datetime.date) -> list[dict]:
        start = datetime.datetime.combine(date_obj, datetime.time.min).timestamp()
        end = datetime.datetime.combine(date_obj, datetime.time.max).timestamp()
        self.cursor.execute(
            '''
            SELECT id, title, description, due_ts, priority, status,
                   remind_before_min, reminder_sent, overdue_sent, created_ts, completed_ts
            FROM tasks
            WHERE due_ts BETWEEN ? AND ?
            ORDER BY due_ts ASC
            ''',
            (start, end),
        )
        cols = [
            "id", "title", "description", "due_ts", "priority", "status",
            "remind_before_min", "reminder_sent", "overdue_sent", "created_ts", "completed_ts",
        ]
        return [dict(zip(cols, row)) for row in self.cursor.fetchall()]

    # Activity insights ------------------------------------------------------
    def get_activity_summary(self, start_ts: float, end_ts: float) -> dict:
        """
        Summary for a selected time range.
        Returns total/productive seconds + top category/app.
        """
        self.cursor.execute(
            '''
            SELECT COALESCE(SUM(duration), 0)
            FROM activity_sessions
            WHERE start_time BETWEEN ? AND ?
            ''',
            (float(start_ts), float(end_ts)),
        )
        total_secs = float(self.cursor.fetchone()[0] or 0.0)

        self.cursor.execute(
            '''
            SELECT COALESCE(SUM(duration), 0)
            FROM activity_sessions
            WHERE start_time BETWEEN ? AND ?
              AND category IN ('coding', 'learning', 'writing', 'communication', 'planning', 'reading')
            ''',
            (float(start_ts), float(end_ts)),
        )
        productive_secs = float(self.cursor.fetchone()[0] or 0.0)

        self.cursor.execute(
            '''
            SELECT category, SUM(duration) AS d
            FROM activity_sessions
            WHERE start_time BETWEEN ? AND ?
            GROUP BY category
            ORDER BY d DESC
            LIMIT 1
            ''',
            (float(start_ts), float(end_ts)),
        )
        top_cat_row = self.cursor.fetchone()
        top_category = top_cat_row[0] if top_cat_row else "none"

        self.cursor.execute(
            '''
            SELECT COALESCE(NULLIF(domain, ''), app) AS target, SUM(duration) AS d
            FROM activity_sessions
            WHERE start_time BETWEEN ? AND ?
            GROUP BY target
            ORDER BY d DESC
            LIMIT 1
            ''',
            (float(start_ts), float(end_ts)),
        )
        top_app_row = self.cursor.fetchone()
        top_app = top_app_row[0] if top_app_row else "none"

        return {
            "total_secs": total_secs,
            "productive_secs": productive_secs,
            "top_category": top_category,
            "top_app": top_app,
        }

    def get_activity_sessions(self, start_ts: float, end_ts: float, limit: int = 500) -> list[dict]:
        """
        Session timeline for selected range.
        """
        self.cursor.execute(
            '''
            SELECT id, start_time, end_time, app, title, domain, category, duration
            FROM activity_sessions
            WHERE start_time BETWEEN ? AND ?
            ORDER BY start_time ASC
            LIMIT ?
            ''',
            (float(start_ts), float(end_ts), int(limit)),
        )
        cols = ["id", "start_time", "end_time", "app", "title", "domain", "category", "duration"]
        return [dict(zip(cols, row)) for row in self.cursor.fetchall()]

    def get_monthly_day_activity_tags(self, year: int, month: int) -> dict:
        """
        Return per-day tags for a calendar month.
        {
          "YYYY-MM-DD": {
              "top_category": "...",
              "total_secs": ...,
              "productive_secs": ...,
              "tag": "productive" | "entertainment" | "mixed"
          }
        }
        """
        first_day = datetime.date(int(year), int(month), 1)
        if month == 12:
            next_month = datetime.date(year + 1, 1, 1)
        else:
            next_month = datetime.date(year, month + 1, 1)

        start_ts = datetime.datetime.combine(first_day, datetime.time.min).timestamp()
        end_ts = datetime.datetime.combine(next_month - datetime.timedelta(days=1), datetime.time.max).timestamp()

        self.cursor.execute(
            '''
            SELECT start_time, category, duration
            FROM activity_sessions
            WHERE start_time BETWEEN ? AND ?
            ORDER BY start_time ASC
            ''',
            (float(start_ts), float(end_ts)),
        )
        rows = self.cursor.fetchall()

        productive_set = {"coding", "learning", "writing", "communication", "planning", "reading"}
        daily = {}
        productive_set = {"coding", "learning", "writing", "communication", "planning", "reading"}
        for st, cat, dur in rows:
            day_key = datetime.datetime.fromtimestamp(float(st)).date().isoformat()
            if day_key not in daily:
                daily[day_key] = {
                    "total_secs": 0.0,
                    "productive_secs": 0.0,
                    "cats": {},
                    "productive_by_hour": [0.0] * 24,
                }
            daily[day_key]["total_secs"] += float(dur or 0.0)
            st_dt = datetime.datetime.fromtimestamp(float(st))
            hour = int(st_dt.hour)
            if str(cat).lower() in productive_set:
                daily[day_key]["productive_secs"] += float(dur or 0.0)
                if 0 <= hour < 24:
                    daily[day_key]["productive_by_hour"][hour] += float(dur or 0.0)
            cat_key = str(cat).lower()
            daily[day_key]["cats"][cat_key] = daily[day_key]["cats"].get(cat_key, 0.0) + float(dur or 0.0)

        out = {}
        for day_key, info in daily.items():
            cats = info["cats"]
            top_cat = max(cats.items(), key=lambda x: x[1])[0] if cats else "unknown"
            total_secs = info["total_secs"]
            prod_secs = info["productive_secs"]
            ratio = (prod_secs / total_secs) if total_secs > 0 else 0.0

            if top_cat in {"entertainment", "browsing"}:
                tag = "entertainment"
            elif ratio >= 0.6:
                tag = "productive"
            else:
                tag = "mixed"

            hour_values = info["productive_by_hour"]
            peak_hour = int(max(range(24), key=lambda i: hour_values[i])) if any(hour_values) else None
            productivity_pct = int(ratio * 100) if total_secs > 0 else 0

            out[day_key] = {
                "top_category": top_cat,
                "total_secs": total_secs,
                "productive_secs": prod_secs,
                "tag": tag,
                "productivity_pct": productivity_pct,
                "peak_hour": peak_hour,
                "productive_by_hour": hour_values,
            }

        return out

    def insert_session(self, start_time: float, end_time: float, app: str, title: str, domain: str, category: str, duration: float):
        """Inserts a completed session into the database."""
        self.cursor.execute('''
            INSERT INTO activity_sessions (start_time, end_time, app, title, domain, category, duration)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (start_time, end_time, app, title, domain, category, duration))
        self.conn.commit()
    
    def cleanup_old_data(self):
        """Purges data older than 1 year."""
        one_year_ago = (datetime.datetime.now() - datetime.timedelta(days=365)).timestamp()
        
        self.cursor.execute('DELETE FROM activity_sessions WHERE start_time < ?', (one_year_ago,))
        
        one_year_ago_date = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
        self.cursor.execute('DELETE FROM daily_stats WHERE date < ?', (one_year_ago_date,))
        
        self.conn.commit()
        self.cursor.execute('VACUUM')
        
    def close(self):
        """Closes the DB connection."""
        self.conn.close()
