from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List

from core.collector.base import BaseSource
from models.company import Company
from models.news import RawNewsItem
from utils.logger import get_logger

logger = get_logger(__name__)

_COMPANY_TIMEOUT = 30


class Aggregator:
    def __init__(self, sources: List[BaseSource], concurrency: int = 8):
        self._sources = [s for s in sources if s.is_available()]
        self._concurrency = concurrency
        unavailable = [s.name for s in sources if not s.is_available()]
        if unavailable:
            logger.info("sources_unavailable", sources=unavailable)

    def collect_all(self, companies: List[Company], start_date: datetime) -> List[RawNewsItem]:
        all_items: List[RawNewsItem] = []
        with ThreadPoolExecutor(max_workers=self._concurrency) as executor:
            future_to_company = {
                executor.submit(self._collect_company, company, start_date): company
                for company in companies
            }
            for future in as_completed(future_to_company):
                company = future_to_company[future]
                try:
                    items = future.result(timeout=_COMPANY_TIMEOUT)
                    all_items.extend(items)
                    logger.info("company_collected", company=company.name, count=len(items))
                except Exception as e:
                    logger.warning("company_collect_error", company=company.name, error=str(e))
        return all_items

    def _collect_company(self, company: Company, start_date: datetime) -> List[RawNewsItem]:
        items = []
        for source in self._sources:
            try:
                fetched = source.fetch(company, start_date)
                items.extend(fetched)
            except Exception as e:
                logger.warning("source_error", source=source.name, company=company.name, error=str(e))
        return items
