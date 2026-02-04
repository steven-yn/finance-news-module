"""뉴스 필터 추상 클래스 및 베이스 구현체"""

from abc import ABC, abstractmethod

from .types import NewsItem


class NewsFilter(ABC):
    """뉴스 필터 추상 클래스

    qfin의 Detector 패턴을 응용한 필터링 인터페이스:
    - should_pass(): 필터 통과 여부
    - 체이닝 가능 (CompositeFilter)
    """

    @abstractmethod
    def should_pass(self, item: NewsItem) -> bool:
        """필터 통과 여부

        Args:
            item: 필터링할 뉴스 아이템

        Returns:
            True: 통과 (알림 발송)
            False: 차단 (알림 발송 안 함)
        """
        pass


class CompositeFilter(NewsFilter):
    """복합 필터 (AND 조건)

    여러 필터를 체이닝하여 모든 조건을 만족해야 통과
    """

    def __init__(self, filters: list[NewsFilter]):
        self.filters = filters

    def should_pass(self, item: NewsItem) -> bool:
        """모든 필터를 통과해야 True"""
        return all(f.should_pass(item) for f in self.filters)

    def add_filter(self, filter: NewsFilter) -> None:
        """필터 추가"""
        self.filters.append(filter)

    def remove_filter(self, filter: NewsFilter) -> None:
        """필터 제거"""
        self.filters.remove(filter)


class PassAllFilter(NewsFilter):
    """모든 뉴스 통과 (기본 필터)"""

    def should_pass(self, item: NewsItem) -> bool:
        return True
