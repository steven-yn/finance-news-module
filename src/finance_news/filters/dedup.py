"""중복 제거 필터

동일하거나 유사한 뉴스의 중복 발송을 방지합니다.

주요 기능:
- 해시 기반 정확한 중복 제거
- 유사도 기반 유사 뉴스 제거
- TTL 기반 캐시 만료
- 메모리 제한 (LRU 방식)
"""

import hashlib
import logging
import time
from collections import OrderedDict
from typing import Optional

from ..core.filter import NewsFilter
from ..core.types import NewsItem

logger = logging.getLogger(__name__)


class DeduplicationFilter(NewsFilter):
    """중복 제거 필터

    해시 기반으로 동일한 뉴스를 필터링합니다.
    """

    def __init__(
        self,
        max_cache_size: int = 10000,
        ttl_seconds: float = 86400.0,  # 24시간
        use_content_hash: bool = True,
    ):
        """
        Args:
            max_cache_size: 최대 캐시 크기 (LRU 방식으로 오래된 것 제거)
            ttl_seconds: 캐시 만료 시간 (초)
            use_content_hash: True면 내용 기반 해시, False면 ID 기반
        """
        self.max_cache_size = max_cache_size
        self.ttl_seconds = ttl_seconds
        self.use_content_hash = use_content_hash

        # OrderedDict로 LRU 캐시 구현 (해시 -> 타임스탬프)
        self._cache: OrderedDict[str, float] = OrderedDict()

        logger.info(f"DeduplicationFilter 초기화: 캐시 크기 {max_cache_size}, TTL {ttl_seconds}초")

    def _compute_hash(self, item: NewsItem) -> str:
        """뉴스 아이템의 해시 계산"""
        if self.use_content_hash:
            # 내용 기반 해시 (헤드라인 + 소스)
            content = f"{item.headline}:{item.source}"
        else:
            # ID 기반 해시
            content = item.id

        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _cleanup_expired(self) -> None:
        """만료된 캐시 항목 제거"""
        current_time = time.time()
        expired_keys = []

        for hash_key, timestamp in self._cache.items():
            if current_time - timestamp > self.ttl_seconds:
                expired_keys.append(hash_key)
            else:
                # OrderedDict는 삽입 순서대로 정렬되므로 이후는 만료되지 않음
                break

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"만료된 캐시 {len(expired_keys)}개 제거")

    def _enforce_max_size(self) -> None:
        """최대 캐시 크기 유지 (LRU 방식)"""
        while len(self._cache) > self.max_cache_size:
            # 가장 오래된 항목 제거
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            logger.debug(f"캐시 크기 초과, 오래된 항목 제거: {oldest_key}")

    def should_pass(self, item: NewsItem) -> bool:
        """중복 여부 확인

        Returns:
            True: 새로운 뉴스 (통과)
            False: 중복 뉴스 (차단)
        """
        # 만료된 항목 정리
        self._cleanup_expired()

        # 해시 계산
        item_hash = self._compute_hash(item)

        # 중복 체크
        if item_hash in self._cache:
            logger.debug(f"중복 뉴스 감지: {item.headline[:50]}...")
            # LRU: 접근 시 순서 갱신
            self._cache.move_to_end(item_hash)
            return False

        # 새로운 뉴스 - 캐시에 추가
        self._cache[item_hash] = time.time()

        # 최대 크기 유지
        self._enforce_max_size()

        return True

    def clear_cache(self) -> None:
        """캐시 초기화"""
        self._cache.clear()
        logger.info("DeduplicationFilter 캐시 초기화")

    @property
    def cache_size(self) -> int:
        """현재 캐시 크기"""
        return len(self._cache)


class SimilarityDeduplicationFilter(NewsFilter):
    """유사도 기반 중복 제거 필터

    헤드라인이 유사한 뉴스를 필터링합니다.
    (간단한 자카드 유사도 사용)
    """

    def __init__(
        self,
        similarity_threshold: float = 0.7,
        max_cache_size: int = 1000,
        ttl_seconds: float = 3600.0,  # 1시간
    ):
        """
        Args:
            similarity_threshold: 유사도 임계값 (0.0 ~ 1.0)
            max_cache_size: 최대 캐시 크기
            ttl_seconds: 캐시 만료 시간
        """
        self.similarity_threshold = similarity_threshold
        self.max_cache_size = max_cache_size
        self.ttl_seconds = ttl_seconds

        # (토큰셋, 타임스탬프) 저장
        self._cache: OrderedDict[str, tuple[set[str], float]] = OrderedDict()

        logger.info(
            f"SimilarityDeduplicationFilter 초기화: "
            f"임계값 {similarity_threshold}, TTL {ttl_seconds}초"
        )

    def _tokenize(self, text: str) -> set[str]:
        """텍스트를 토큰셋으로 변환"""
        # 소문자 변환 + 알파벳/숫자만 추출
        text = text.lower()
        tokens = set()
        current_token = []

        for char in text:
            if char.isalnum():
                current_token.append(char)
            elif current_token:
                tokens.add("".join(current_token))
                current_token = []

        if current_token:
            tokens.add("".join(current_token))

        return tokens

    def _jaccard_similarity(self, set1: set[str], set2: set[str]) -> float:
        """자카드 유사도 계산"""
        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    def _cleanup_expired(self) -> None:
        """만료된 캐시 항목 제거"""
        current_time = time.time()
        expired_keys = []

        for key, (_, timestamp) in self._cache.items():
            if current_time - timestamp > self.ttl_seconds:
                expired_keys.append(key)
            else:
                break

        for key in expired_keys:
            del self._cache[key]

    def should_pass(self, item: NewsItem) -> bool:
        """유사도 기반 중복 체크"""
        self._cleanup_expired()

        # 현재 아이템 토큰화
        current_tokens = self._tokenize(item.headline)

        if not current_tokens:
            return True

        # 기존 아이템들과 유사도 비교
        for cache_id, (cached_tokens, _) in self._cache.items():
            similarity = self._jaccard_similarity(current_tokens, cached_tokens)

            if similarity >= self.similarity_threshold:
                logger.debug(f"유사 뉴스 감지 (유사도: {similarity:.2f}): {item.headline[:50]}...")
                return False

        # 새로운 뉴스 - 캐시에 추가
        self._cache[item.id] = (current_tokens, time.time())

        # 최대 크기 유지
        while len(self._cache) > self.max_cache_size:
            self._cache.popitem(last=False)

        return True

    def clear_cache(self) -> None:
        """캐시 초기화"""
        self._cache.clear()
        logger.info("SimilarityDeduplicationFilter 캐시 초기화")
