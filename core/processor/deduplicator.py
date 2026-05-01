import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from models.news import RawNewsItem
from utils.logger import get_logger

logger = get_logger(__name__)


class Deduplicator:
    def __init__(self, db_path: str = "data/cache/news_cache.db", retention_days: int = 90):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._retention_days = retention_days
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS seen_news (
                url_hash     TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL,
                url          TEXT NOT NULL,
                title        TEXT NOT NULL,
                crawled_at   TEXT NOT NULL,
                expires_at   TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_expires ON seen_news(expires_at);
            CREATE INDEX IF NOT EXISTS idx_content ON seen_news(content_hash);
        """)
        self._conn.commit()

    def is_duplicate(self, item: RawNewsItem) -> bool:
        self._cleanup_expired()
        cur = self._conn.execute(
            "SELECT 1 FROM seen_news WHERE url_hash=? OR content_hash=?",
            (item.id, item.content_hash),
        )
        return cur.fetchone() is not None

    def mark_seen(self, item: RawNewsItem) -> None:
        now = datetime.now()
        expires = now + timedelta(days=self._retention_days)
        self._conn.execute(
            """INSERT OR REPLACE INTO seen_news
               (url_hash, content_hash, url, title, crawled_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (item.id, item.content_hash, item.url, item.title,
             now.isoformat(), expires.isoformat()),
        )
        self._conn.commit()

    def _cleanup_expired(self) -> int:
        cur = self._conn.execute(
            "DELETE FROM seen_news WHERE expires_at < ?",
            (datetime.now().isoformat(),),
        )
        self._conn.commit()
        return cur.rowcount

    def cleanup_expired(self) -> int:
        return self._cleanup_expired()

    def close(self) -> None:
        self._conn.close()
