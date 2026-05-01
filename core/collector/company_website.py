from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from core.collector.base import BaseSource
from core.collector.web_scraper import WebScraper
from models.company import Company
from models.news import RawNewsItem
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WebsiteConfig:
    url: str
    article_selector: str = ".news-list .item"
    title_selector: str = ".title"
    link_selector: str = "a"
    date_selector: str = ".date"
    use_playwright: bool = False


class CompanyWebsiteSource(BaseSource):
    name = "company_website"

    def __init__(self, configs: Dict[str, WebsiteConfig], scraper: Optional[WebScraper] = None):
        self._configs = configs
        self._scraper = scraper or WebScraper()

    def fetch(self, company: Company, start_date: datetime) -> List[RawNewsItem]:
        cfg = self._configs.get(company.name)
        if not cfg or not cfg.url:
            return []
        try:
            return self._fetch_from_config(company, cfg)
        except Exception as e:
            logger.warning("company_website_error", company=company.name, error=str(e))
            return []

    def _fetch_from_config(self, company: Company, cfg: WebsiteConfig) -> List[RawNewsItem]:
        resp = requests.get(cfg.url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        items = []
        for article in soup.select(cfg.article_selector)[:20]:
            title_el = article.select_one(cfg.title_selector)
            link_el = article.select_one(cfg.link_selector)
            if not title_el or not link_el:
                continue
            title = title_el.get_text(strip=True)
            href = link_el.get("href", "")
            if href and not href.startswith("http"):
                href = urljoin(cfg.url, href)
            content = self._scraper.fetch_url(href) if href else ""
            items.append(RawNewsItem(
                title=title,
                url=href,
                content=content,
                source_name=f"{company.name}官网",
                source_type="website",
                company_name=company.name,
                published_at=None,
            ))
        return items
