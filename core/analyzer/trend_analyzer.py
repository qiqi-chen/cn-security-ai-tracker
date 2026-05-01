from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from models.company import Company
from models.news import ProcessedNewsItem
from models.report import AnalysisResult
from utils.keywords import STOPWORDS
from utils.logger import get_logger

logger = get_logger(__name__)


class TrendAnalyzer:
    def __init__(self, window_days: int = 7, threshold: float = 0.5, top_keywords_count: int = 20):
        self._window_days = window_days
        self._threshold = threshold
        self._top_keywords_count = top_keywords_count

    def analyze(
        self,
        items: List[ProcessedNewsItem],
        companies: List[Company],
        stats: Dict[str, Any],
    ) -> AnalysisResult:
        if not items:
            return AnalysisResult(trends=["本期暂无显著行业趋势"])

        trends = []
        trends.extend(self._category_trends(stats.get("category_stats", {})))
        active_surge = self._detect_surge(items)
        trends.extend([f"{c}近期动态密集，活跃度显著提升" for c in active_surge])
        co_mentioned = self._co_mentioned(items)
        for a, b, n in co_mentioned[:3]:
            trends.append(f"{a}与{b}在同一事件中共同出现 {n} 次")

        if not trends:
            trends = ["本期暂无显著行业趋势"]

        keywords = self._extract_keywords(items)

        return AnalysisResult(
            trends=trends,
            category_stats=stats.get("category_stats", {}),
            company_activity=stats.get("company_activity", {}),
            top_keywords=keywords,
            co_mentioned=co_mentioned,
            active_surge=active_surge,
            avg_quality_score=stats.get("avg_quality_score", 0.0),
        )

    def _category_trends(self, category_stats: Dict[str, int]) -> List[str]:
        top = sorted(category_stats.items(), key=lambda x: x[1], reverse=True)[:3]
        return [f"{cat}成为本期热点，共 {cnt} 条相关报道" for cat, cnt in top if cnt > 0]

    def _detect_surge(self, items: List[ProcessedNewsItem]) -> List[str]:
        cutoff = datetime.now() - timedelta(days=self._window_days)
        recent_counts: Counter = Counter()
        total_counts: Counter = Counter()
        for item in items:
            total_counts[item.company_name] += 1
            if item.published_at and item.published_at.replace(tzinfo=None) >= cutoff:
                recent_counts[item.company_name] += 1
        surge = []
        for company, total in total_counts.items():
            if total > 0 and recent_counts.get(company, 0) / total >= self._threshold:
                surge.append(company)
        return surge

    def _co_mentioned(self, items: List[ProcessedNewsItem]) -> List[Tuple[str, str, int]]:
        pair_counts: Counter = Counter()
        for item in items:
            companies = sorted(set(item.related_companies))
            for i in range(len(companies)):
                for j in range(i + 1, len(companies)):
                    pair_counts[(companies[i], companies[j])] += 1
        return [(a, b, n) for (a, b), n in pair_counts.most_common(10)]

    def _extract_keywords(self, items: List[ProcessedNewsItem]) -> List[str]:
        try:
            import jieba
            word_counts: Counter = Counter()
            for item in items:
                text = item.title + " " + item.cleaned_content[:500]
                words = jieba.cut(text)
                for w in words:
                    w = w.strip()
                    if len(w) >= 2 and w not in STOPWORDS:
                        word_counts[w] += 1
            return [w for w, _ in word_counts.most_common(self._top_keywords_count)]
        except ImportError:
            return []
