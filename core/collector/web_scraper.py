import requests
from bs4 import BeautifulSoup
from utils.retry import retry_with_backoff, RetryConfig
from utils.logger import get_logger

logger = get_logger(__name__)

_NOISE_SELECTORS = ["script", "style", "nav", "footer", "header", "aside"]


class WebScraper:
    def __init__(self, timeout: int = 10):
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; SecurityNewsBot/1.0)"})

    @retry_with_backoff(RetryConfig(max_retries=2, base_delay=1.0))
    def fetch_url(self, url: str) -> str:
        try:
            resp = self._session.get(url, timeout=self._timeout)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or resp.encoding
            return self._extract_text(resp.text)
        except Exception as e:
            logger.warning("web_scraper_error", url=url, error=str(e))
            return ""

    def _extract_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(_NOISE_SELECTORS):
            tag.decompose()
        for selector in ["article", "main", '[class*="content"]', '[class*="article"]', '[class*="post"]']:
            el = soup.select_one(selector)
            if el and len(el.get_text(strip=True)) > 100:
                return el.get_text(separator="\n", strip=True)[:5000]
        return soup.get_text(separator="\n", strip=True)[:3000]
