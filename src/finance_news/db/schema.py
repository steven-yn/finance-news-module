"""SQLite 데이터베이스 스키마 정의"""

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

CREATE_NEWS_TABLE = """
CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    news_id TEXT NOT NULL UNIQUE,
    hash TEXT NOT NULL,
    headline TEXT NOT NULL,
    summary TEXT,
    url TEXT,
    source TEXT NOT NULL,
    category TEXT NOT NULL,
    published_at TIMESTAMP NOT NULL,
    symbols TEXT,
    raw_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notified_at TIMESTAMP
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_news_hash ON news(hash);",
    "CREATE INDEX IF NOT EXISTS idx_news_published_at ON news(published_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_news_source ON news(source);",
    "CREATE INDEX IF NOT EXISTS idx_news_category ON news(category);",
    "CREATE INDEX IF NOT EXISTS idx_news_created_at ON news(created_at DESC);",
]

CREATE_SCHEMA_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    """데이터베이스 초기화 및 연결 반환

    Args:
        db_path: SQLite 데이터베이스 파일 경로

    Returns:
        sqlite3.Connection
    """
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA cache_size=10000;")

    conn.execute(CREATE_SCHEMA_VERSION_TABLE)
    conn.execute(CREATE_NEWS_TABLE)

    for index_sql in CREATE_INDEXES:
        conn.execute(index_sql)

    cursor = conn.execute("SELECT MAX(version) FROM schema_version")
    row = cursor.fetchone()
    current_version = row[0] if row[0] else 0

    if current_version < SCHEMA_VERSION:
        conn.execute(
            "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
            (SCHEMA_VERSION,),
        )
        conn.commit()
        logger.info(f"데이터베이스 스키마 버전 {SCHEMA_VERSION} 적용 완료")

    logger.info(f"데이터베이스 초기화 완료: {db_path}")
    return conn
