from datetime import datetime
from typing import List

from core.collector.base import BaseSource
from models.company import Company
from models.news import RawNewsItem
from utils.logger import get_logger

logger = get_logger(__name__)


class PlaywrightSource(BaseSource):
    name = "playwright"

    def is_available(self) -> bool:
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
            return True
        except ImportError:
            return False

    def fetch(self, company: Company, start_date: datetime) -> List[RawNewsItem]:
        if not self.is_available():
            return []
        logger.warning("playwright_fetch_not_implemented", company=company.name)
        return []

    def fetch_url(self, url: str, selector: str = "body") -> str:
        if not self.is_available():
            return ""
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=30000)
                page.wait_for_selector(selector, timeout=10000)
                content = page.inner_text(selector)
                browser.close()
                return content
        except Exception as e:
            logger.warning("playwright_error", url=url, error=str(e))
            return ""
