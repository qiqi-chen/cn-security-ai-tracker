import requests
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlencode
from dateutil import parser as dateutil_parser

from core.collector.base import BaseSource
from models.company import Company
from models.news import RawNewsItem
from utils.keywords import LARGE_COMPANY_NAMES
from utils.logger import get_logger

logger = get_logger(__name__)


class SearxngSource(BaseSource):
    name = "searxng"

    def __init__(self, base_url: str, search_limit: int = 10, timeout: int = 10):
        self._base_url = base_url.rstrip("/")
        self._search_limit = search_limit
        self._timeout = timeout

    def is_available(self) -> bool:
        try:
            r = requests.get(f"{self._base_url}/healthz", timeout=3)
            return r.status_code < 500
        except Exception:
            return False

    def fetch(self, company: Company, start_date: datetime) -> List[RawNewsItem]:
        query = self._build_query(company)
        try:
            results = self._search(query)
        except Exception as e:
            logger.warning("searxng_fetch_error", company=company.name, error=str(e))
            return []
        items = []
        for r in results:
            pub = self._parse_date(r.get("publishedDate", ""))
            if pub and pub < start_date:
                continue
            items.append(RawNewsItem(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
                source_name=r.get("engine", "searxng"),
                source_type="searxng",
                company_name=company.name,
                published_at=pub,
            ))
        return items

    def _build_query(self, company: Company) -> str:
        names = f"({company.name} {company.english_name})"
        ai_part = "(AI 人工智能 大模型 LLM 智能安全)"
        query = f"{names} {ai_part}"
        if company.name in LARGE_COMPANY_NAMES:
            query += " 安全"
        return query

    def _search(self, query: str) -> list:
        params = {"q": query, "format": "json", "count": self._search_limit}
        url = f"{self._base_url}/search?{urlencode(params)}"
        resp = requests.get(url, timeout=self._timeout)
        resp.raise_for_status()
        return resp.json().get("results", [])

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return dateutil_parser.parse(date_str)
        except Exception:
            return None
