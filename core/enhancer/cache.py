import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class LLMCache:
    def __init__(self, db_path: str = "data/cache/llm_cache.db"):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_cache (
                content_hash TEXT PRIMARY KEY,
                summary      TEXT NOT NULL,
                key_points   TEXT NOT NULL,
                created_at   TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def get(self, content_hash: str) -> Optional[Dict]:
        cur = self._conn.execute(
            "SELECT summary, key_points FROM llm_cache WHERE content_hash=?",
            (content_hash,),
        )
        row = cur.fetchone()
        if row:
            return {"summary": row[0], "key_points": json.loads(row[1])}
        return None

    def set(self, content_hash: str, summary: str, key_points: List[str]) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO llm_cache (content_hash, summary, key_points, created_at) VALUES (?, ?, ?, ?)",
            (content_hash, summary, json.dumps(key_points, ensure_ascii=False), datetime.now().isoformat()),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
