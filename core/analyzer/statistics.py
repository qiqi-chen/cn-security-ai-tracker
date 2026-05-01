from collections import Counter
from typing import Any, Dict, List

from models.company import Company
from models.news import ProcessedNewsItem


class StatisticsCalculator:
    def compute(self, items: List[ProcessedNewsItem], companies: List[Company]) -> Dict[str, Any]:
        active = {item.company_name for item in items}
        category_counts: Counter = Counter()
        company_counts: Counter = Counter()
        source_counts: Counter = Counter()
        quality_sum = 0.0

        for item in items:
            for cat in item.categories:
                category_counts[cat] += 1
            company_counts[item.company_name] += 1
            source_counts[item.raw.source_type] += 1
            quality_sum += item.quality_score

        avg_quality = quality_sum / len(items) if items else 0.0

        return {
            "total_news": len(items),
            "active_companies": len(active),
            "category_stats": dict(category_counts.most_common()),
            "company_activity": dict(company_counts.most_common()),
            "avg_quality_score": round(avg_quality, 3),
            "source_distribution": dict(source_counts),
        }
