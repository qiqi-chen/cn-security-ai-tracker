from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import hashlib

@dataclass
class RawNewsItem:
    title: str
    url: str
    content: str
    source_name: str
    source_type: str        # rss / searxng / website / playwright
    company_name: str
    published_at: Optional[datetime] = None
    crawled_at: datetime = field(default_factory=datetime.now)
    raw_html: str = ""

    @property
    def content_hash(self) -> str:
        return hashlib.md5(self.content.encode("utf-8")).hexdigest()

    @property
    def id(self) -> str:
        return hashlib.md5(self.url.encode("utf-8")).hexdigest()[:16]


@dataclass
class ProcessedNewsItem:
    raw: RawNewsItem
    cleaned_content: str
    related_companies: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    is_duplicate: bool = False
    summary: str = ""
    key_points: List[str] = field(default_factory=list)

    @property
    def title(self) -> str:
        return self.raw.title

    @property
    def url(self) -> str:
        return self.raw.url

    @property
    def source_name(self) -> str:
        return self.raw.source_name

    @property
    def published_at(self) -> Optional[datetime]:
        return self.raw.published_at

    @property
    def company_name(self) -> str:
        return self.raw.company_name

    @property
    def content_preview(self) -> str:
        text = self.cleaned_content or self.raw.content
        text = text.strip()
        return text[:150] + "…" if len(text) > 150 else text
