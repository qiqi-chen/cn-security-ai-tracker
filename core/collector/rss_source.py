import requests
from datetime import datetime
from typing import List, Optional, Dict
from dateutil import parser as dateutil_parser
from bs4 import BeautifulSoup

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False

from core.collector.base import BaseSource
from models.company import Company
from models.news import RawNewsItem
from utils.keywords import AI_KEYWORDS
from utils.retry import retry_with_backoff, RetryConfig
from utils.logger import get_logger

logger = get_logger(__name__)

_RETRY = RetryConfig(max_retries=2, base_delay=1.0)


class RSSSource(BaseSource):
    name = "rss"

    def __init__(self, feeds: List[Dict], timeout: int = 10):
        self._feeds = feeds
        self._timeout = timeout

    def fetch(self, company: Company, start_date: datetime) -> List[RawNewsItem]:
        if not FEEDPARSER_AVAILABLE:
            return []
        results = []
        for feed_cfg in self._feeds:
            if not feed_cfg.get("enabled", True):
                continue
            try:
                results.extend(self._fetch_feed(feed_cfg, company, start_date))
            except Exception as e:
                logger.warning("rss_feed_error", feed=feed_cfg.get("name"), error=str(e))
        return results

    def _fetch_feed(self, feed_cfg: Dict, company: Company, start_date: datetime) -> List[RawNewsItem]:
        parsed = feedparser.parse(feed_cfg["url"])
        items = []
        for entry in parsed.entries:
            pub_date = self._parse_date(entry)
            if pub_date and pub_date < start_date:
                continue
            text = f"{entry.get('title', '')} {entry.get('summary', '')}"
            if not self._is_relevant(text, company):
                continue
            content = entry.get("summary", "")
            if feed_cfg.get("scrape_full_content") and entry.get("link"):
                scraped = self._scrape_content(entry["link"])
                if scraped:
                    content = scraped
            items.append(RawNewsItem(
                title=entry.get("title", ""),
                url=entry.get("link", ""),
                content=content,
                source_name=feed_cfg["name"],
                source_type="rss",
                company_name=company.name,
                published_at=pub_date,
            ))
        return items

    def _is_relevant(self, text: str, company: Company) -> bool:
        return any(n.lower() in text.lower() for n in company.all_names())

    def _parse_date(self, entry) -> Optional[datetime]:
        for attr in ("published_parsed", "updated_parsed"):
            val = getattr(entry, attr, None)
            if val:
                try:
                    import time as _time
                    return datetime.fromtimestamp(_time.mktime(val))
                except Exception:
                    pass
        for attr in ("published", "updated"):
            val = getattr(entry, attr, None)
            if val:
                try:
                    return dateutil_parser.parse(val)
                except Exception:
                    pass
        return None

    @retry_with_backoff(RetryConfig(max_retries=2, base_delay=1.0))
    def _scrape_content(self, url: str) -> str:
        resp = requests.get(url, timeout=self._timeout, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        for selector in ["article", "main", '[class*="content"]', '[class*="article"]']:
            el = soup.select_one(selector)
            if el:
                return el.get_text(separator="\n", strip=True)
        return soup.get_text(separator="\n", strip=True)[:3000]
