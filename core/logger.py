import sqlite3
from datetime import date, datetime, timedelta
from collections import defaultdict
import os


class SessionLogger:
    def __init__(self, db_path=None):
        if db_path is None:
            # مسیر استاندارد داده‌های کاربر
            data_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "focusguardian")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "sessions.db")
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()          # ← این خط را اضافه کنید

        
        # جدول اصلی
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                start_time TEXT,
                end_time TEXT,
                duration_seconds INTEGER,
                target_duration INTEGER DEFAULT 0,
                status TEXT,
                distraction_attempts INTEGER DEFAULT 0,
                streak_id TEXT,
                streak_position INTEGER DEFAULT 1,
                overtime_seconds INTEGER DEFAULT 0,
                break_after_seconds INTEGER DEFAULT 0,
                rest_completed INTEGER DEFAULT 0
            )
        """)
        # اضافه کردن ستون‌های جدید در صورت وجود نداشتن (migration)
        self._add_column_if_not_exists("target_duration", "INTEGER DEFAULT 0")
        self._add_column_if_not_exists("distraction_attempts", "INTEGER DEFAULT 0")
        self._add_column_if_not_exists("streak_id", "TEXT")
        self._add_column_if_not_exists("streak_position", "INTEGER DEFAULT 1")
        self._add_column_if_not_exists("overtime_seconds", "INTEGER DEFAULT 0")
        self._add_column_if_not_exists("break_after_seconds", "INTEGER DEFAULT 0")
        self._add_column_if_not_exists("rest_completed", "INTEGER DEFAULT 0")
        self.conn.commit()

    def _add_column_if_not_exists(self, column_name, column_type):
        try:
            self.cursor.execute(f"ALTER TABLE sessions ADD COLUMN {column_name} {column_type}")
        except sqlite3.OperationalError:
            pass  # ستون قبلاً وجود دارد

    def log_session(self, duration_seconds, status, target_duration=None,
                    distraction_attempts=0, streak_id=None, streak_position=1,
                    overtime_seconds=0, break_after_seconds=0, rest_completed=0):
        now = datetime.now()
        start = now.timestamp() - duration_seconds
        start_str = datetime.fromtimestamp(start).isoformat()
        if target_duration is None:
            target_duration = duration_seconds
        self.cursor.execute(
            "INSERT INTO sessions (date, start_time, end_time, duration_seconds, target_duration, status, distraction_attempts, streak_id, streak_position, overtime_seconds, break_after_seconds, rest_completed) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (date.today().isoformat(), start_str, now.isoformat(), duration_seconds,
             target_duration, status, distraction_attempts, streak_id, streak_position,
             overtime_seconds, break_after_seconds, 1 if rest_completed else 0)
        )
        self.conn.commit()

    def get_daily_stats(self):
        today = date.today().isoformat()
        self.cursor.execute(
            "SELECT status, SUM(duration_seconds) FROM sessions WHERE date = ? GROUP BY status",
            (today,)
        )
        rows = self.cursor.fetchall()
        stats = {"complete": 0, "incomplete": 0}
        for status, total in rows:
            stats[status] = total
        return stats

    def get_today_sessions(self):
        today = date.today().isoformat()
        self.cursor.execute(
            "SELECT duration_seconds, target_duration, status, distraction_attempts FROM sessions WHERE date = ?",
            (today,)
        )
        return self.cursor.fetchall()

    def get_weekly_daily_totals(self):
        """مجموع دقایق کامل هر روز برای ۷ روز گذشته"""
        end = date.today()
        start = end - timedelta(days=6)
        self.cursor.execute(
            "SELECT date, SUM(duration_seconds) FROM sessions WHERE status='complete' AND date BETWEEN ? AND ? GROUP BY date ORDER BY date",
            (start.isoformat(), end.isoformat())
        )
        rows = self.cursor.fetchall()
        totals = defaultdict(int)
        for d, sec in rows:
            totals[d] = sec // 60
        result = []
        for i in range(7):
            day = (start + timedelta(days=i)).isoformat()
            result.append((day, totals.get(day, 0)))
        return result

    def get_hourly_heatmap_data(self, days=30):
        """دقایق جلسات کامل در هر ساعت (۰-۲۳)"""
        since = (date.today() - timedelta(days=days)).isoformat()
        self.cursor.execute(
            "SELECT start_time, duration_seconds FROM sessions WHERE status='complete' AND date >= ?",
            (since,)
        )
        rows = self.cursor.fetchall()
        hour_counts = defaultdict(int)
        for start_str, dur in rows:
            try:
                dt = datetime.fromisoformat(start_str)
                hour = dt.hour
                hour_counts[hour] += dur // 60
            except:
                pass
        return [hour_counts.get(h, 0) for h in range(24)]

    def get_completed_durations(self, days=30):
        """طول جلسات کامل (دقیقه) برای هیستوگرام"""
        since = (date.today() - timedelta(days=days)).isoformat()
        self.cursor.execute(
            "SELECT duration_seconds FROM sessions WHERE status='complete' AND date >= ?",
            (since,)
        )
        return [row[0] // 60 for row in self.cursor.fetchall()]

    def get_focus_score_today(self):
        """میانگین Focus Score جلسات امروز"""
        sessions = self.get_today_sessions()
        if not sessions:
            return 0
        scores = []
        for dur, target, status, dist in sessions:
            completion = (dur / target * 100) if target > 0 else 100
            completion = min(completion, 100)
            score = (completion * 0.7) - (dist * 2)
            scores.append(max(0, min(100, score)))
        return int(sum(scores) / len(scores))

    def get_average_session_length(self, days=30):
        """میانگین طول جلسات کامل (دقیقه)"""
        durs = self.get_completed_durations(days)
        if durs:
            return sum(durs) / len(durs)
        return 0