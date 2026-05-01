from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from jinja2 import Environment, FileSystemLoader

from models.company import Company
from models.news import ProcessedNewsItem
from models.report import Report


class MarkdownReporter:
    def __init__(self, max_news_per_company: int = 5, sort_by: str = "quality",
                 include_empty_companies: bool = False):
        self._max_news = max_news_per_company
        self._sort_by = sort_by
        self._include_empty = include_empty_companies
        template_dir = Path(__file__).parent / "templates"
        self._env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=False)

    def generate(self, report: Report) -> str:
        news_by_company = self._group_by_company(report.news_items, report.companies)
        company_english_names = {c.name: c.english_name for c in report.companies}
        tpl = self._env.get_template("report.md.j2")
        return tpl.render(
            period_start=report.period_start.strftime("%Y年%-m月%-d日"),
            period_end=report.period_end.strftime("%Y年%-m月%-d日"),
            generated_at=report.generated_at.strftime("%Y-%m-%d %H:%M"),
            total_companies_monitored=report.total_companies_monitored,
            total_news_collected=report.total_news_collected,
            active_companies_count=report.active_companies_count,
            analysis=report.analysis,
            news_by_company=news_by_company,
            company_english_names=company_english_names,
        )

    def _group_by_company(
        self,
        items: List[ProcessedNewsItem],
        companies: List[Company],
    ) -> Dict[str, List[ProcessedNewsItem]]:
        grouped: Dict[str, List[ProcessedNewsItem]] = defaultdict(list)
        for item in items:
            grouped[item.company_name].append(item)

        if self._sort_by == "quality":
            sort_key = lambda x: x.quality_score
        else:
            sort_key = lambda x: (x.published_at is None, x.published_at)

        result = {}
        for company in companies:
            company_items = sorted(grouped.get(company.name, []), key=sort_key, reverse=True)
            company_items = company_items[:self._max_news]
            if company_items or self._include_empty:
                result[company.name] = company_items

        return result
