from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple

@dataclass
class AnalysisResult:
    trends: List[str] = field(default_factory=list)
    category_stats: Dict[str, int] = field(default_factory=dict)
    company_activity: Dict[str, int] = field(default_factory=dict)
    top_keywords: List[str] = field(default_factory=list)
    co_mentioned: List[Tuple[str, str, int]] = field(default_factory=list)
    active_surge: List[str] = field(default_factory=list)
    avg_quality_score: float = 0.0


@dataclass
class Report:
    title: str
    period_start: datetime
    period_end: datetime
    generated_at: datetime = field(default_factory=datetime.now)
    companies: List = field(default_factory=list)
    news_items: List = field(default_factory=list)
    analysis: AnalysisResult = field(default_factory=AnalysisResult)
    total_companies_monitored: int = 0
    total_news_collected: int = 0
    active_companies_count: int = 0
