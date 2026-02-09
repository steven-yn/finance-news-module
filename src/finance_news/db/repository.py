"""뉴스 데이터 저장소 (Repository 패턴)"""

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from ..core.types import NewsCategory, NewsItem

logger = logging.getLogger(__name__)


class SafeJSONEncoder(json.JSONEncoder):
    """datetime, Timestamp 등을 안전하게 직렬화하는 JSON 인코더"""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        if hasattr(obj, "__str__"):
            return str(obj)
        return super().default(obj)


class NewsRepository:
    """뉴스 데이터 저장소

    SQLite 기반 뉴스 CRUD 및 중복 체크 기능 제공
    """

    def __init__(self, conn: sqlite3.Connection):
        """
        Args:
            conn: SQLite 연결 객체
        """
        self.conn = conn

    def _compute_hash(self, item: NewsItem) -> str:
        """뉴스 아이템의 고유 해시 계산 (중복 체크용)"""
        content = f"{item.headline}:{item.source}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def _row_to_news_item(self, row: sqlite3.Row) -> NewsItem:
        """DB Row를 NewsItem으로 변환"""
        symbols = json.loads(row["symbols"]) if row["symbols"] else []
        raw = json.loads(row["raw_data"]) if row["raw_data"] else {}

        published_at = row["published_at"]
        if isinstance(published_at, str):
            published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))

        return NewsItem(
            id=row["news_id"],
            headline=row["headline"],
            summary=row["summary"],
            url=row["url"],
            source=row["source"],
            category=NewsCategory(row["category"]),
            published_at=published_at,
            symbols=symbols,
            raw=raw,
        )

    def exists(self, item: NewsItem) -> bool:
        """뉴스 중복 여부 확인 (ID 또는 해시 기반)

        Args:
            item: 확인할 뉴스 아이템

        Returns:
            True if exists, False otherwise
        """
        item_hash = self._compute_hash(item)
        cursor = self.conn.execute(
            "SELECT 1 FROM news WHERE news_id = ? OR hash = ? LIMIT 1",
            (item.id, item_hash),
        )
        return cursor.fetchone() is not None

    def save(self, item: NewsItem, notified: bool = False) -> bool:
        """뉴스 저장 (중복 시 무시)

        Args:
            item: 저장할 뉴스 아이템
            notified: 알림 발송 여부

        Returns:
            True if saved, False if duplicate
        """
        if self.exists(item):
            return False

        item_hash = self._compute_hash(item)
        symbols_json = json.dumps(item.symbols) if item.symbols else None
        raw_json = json.dumps(item.raw, cls=SafeJSONEncoder) if item.raw else None
        notified_at = datetime.now(timezone.utc).isoformat() if notified else None

        try:
            self.conn.execute(
                """
                INSERT INTO news (
                    news_id, hash, headline, summary, url, source,
                    category, published_at, symbols, raw_data, notified_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.id,
                    item_hash,
                    item.headline,
                    item.summary,
                    item.url,
                    item.source,
                    item.category.value,
                    item.published_at.isoformat(),
                    symbols_json,
                    raw_json,
                    notified_at,
                ),
            )
            self.conn.commit()
            logger.debug(f"뉴스 저장 완료: {item.headline[:50]}...")
            return True
        except sqlite3.IntegrityError:
            logger.debug(f"중복 뉴스 무시: {item.headline[:50]}...")
            return False

    def mark_notified(self, item: NewsItem) -> None:
        """알림 발송 완료 표시"""
        self.conn.execute(
            "UPDATE news SET notified_at = ? WHERE news_id = ?",
            (datetime.now(timezone.utc).isoformat(), item.id),
        )
        self.conn.commit()

    def find_recent(
        self,
        limit: int = 100,
        source: Optional[str] = None,
        category: Optional[NewsCategory] = None,
    ) -> list[NewsItem]:
        """최근 뉴스 조회

        Args:
            limit: 최대 조회 개수
            source: 소스 필터 (선택)
            category: 카테고리 필터 (선택)

        Returns:
            NewsItem 리스트 (최신순)
        """
        query = "SELECT * FROM news WHERE 1=1"
        params: list = []

        if source:
            query += " AND source = ?"
            params.append(source)

        if category:
            query += " AND category = ?"
            params.append(category.value)

        query += " ORDER BY published_at DESC LIMIT ?"
        params.append(limit)

        cursor = self.conn.execute(query, params)
        return [self._row_to_news_item(row) for row in cursor.fetchall()]

    def find_by_keyword(self, keyword: str, limit: int = 50) -> list[NewsItem]:
        """키워드로 뉴스 검색

        Args:
            keyword: 검색 키워드
            limit: 최대 조회 개수

        Returns:
            NewsItem 리스트
        """
        cursor = self.conn.execute(
            """
            SELECT * FROM news
            WHERE headline LIKE ? OR summary LIKE ?
            ORDER BY published_at DESC
            LIMIT ?
            """,
            (f"%{keyword}%", f"%{keyword}%", limit),
        )
        return [self._row_to_news_item(row) for row in cursor.fetchall()]

    def count(self, source: Optional[str] = None) -> int:
        """뉴스 개수 조회

        Args:
            source: 소스 필터 (선택)

        Returns:
            뉴스 개수
        """
        if source:
            cursor = self.conn.execute("SELECT COUNT(*) FROM news WHERE source = ?", (source,))
        else:
            cursor = self.conn.execute("SELECT COUNT(*) FROM news")
        return cursor.fetchone()[0]

    def delete_old(self, days: int = 30) -> int:
        """오래된 뉴스 삭제

        Args:
            days: 보관 일수

        Returns:
            삭제된 개수
        """
        cursor = self.conn.execute(
            """
            DELETE FROM news
            WHERE created_at < datetime('now', ?)
            """,
            (f"-{days} days",),
        )
        self.conn.commit()
        deleted = cursor.rowcount
        if deleted > 0:
            logger.info(f"{days}일 이전 뉴스 {deleted}개 삭제")
        return deleted

    def get_stats(self) -> dict:
        """통계 정보 조회"""
        total = self.count()

        cursor = self.conn.execute(
            "SELECT source, COUNT(*) as cnt FROM news GROUP BY source ORDER BY cnt DESC"
        )
        by_source = {row["source"]: row["cnt"] for row in cursor.fetchall()}

        cursor = self.conn.execute(
            "SELECT category, COUNT(*) as cnt FROM news GROUP BY category ORDER BY cnt DESC"
        )
        by_category = {row["category"]: row["cnt"] for row in cursor.fetchall()}

        cursor = self.conn.execute("SELECT COUNT(*) FROM news WHERE notified_at IS NOT NULL")
        notified = cursor.fetchone()[0]

        return {
            "total": total,
            "notified": notified,
            "by_source": by_source,
            "by_category": by_category,
        }
