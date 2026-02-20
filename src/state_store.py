import sqlite3
from datetime import datetime, timedelta, timezone


class StateStore:
    def __init__(self, path: str) -> None:
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sent_reminders (
                dedupe_key TEXT PRIMARY KEY,
                sent_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def already_sent(self, dedupe_key: str) -> bool:
        row = self.conn.execute(
            "SELECT dedupe_key FROM sent_reminders WHERE dedupe_key = ?",
            (dedupe_key,),
        ).fetchone()
        return row is not None

    def mark_sent(self, dedupe_key: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT OR REPLACE INTO sent_reminders(dedupe_key, sent_at) VALUES (?, ?)",
            (dedupe_key, now),
        )
        self.conn.commit()

    def cleanup(self, keep_days: int = 21) -> None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=keep_days)).isoformat()
        self.conn.execute(
            "DELETE FROM sent_reminders WHERE sent_at < ?",
            (cutoff,),
        )
        self.conn.commit()
