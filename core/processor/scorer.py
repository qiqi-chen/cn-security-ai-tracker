from datetime import datetime
from typing import List
from models.news import RawNewsItem

_TRUSTED_SOURCES: List[str] = [
    "官网", "新华网", "人民网", "36kr", "钛媒体",
    "安全客", "嘶吼", "安全脉搏", "FreeBuf", "安全牛",
]


class Scorer:
    def score(self, item: RawNewsItem, cleaned_content: str) -> float:
        s = 0.4
        length = len(cleaned_content)
        if length >= 500:
            s += 0.2
        elif length >= 200:
            s += 0.1

        if any(src in item.source_name for src in _TRUSTED_SOURCES):
            s += 0.2

        if item.published_at:
            delta = (datetime.now() - item.published_at.replace(tzinfo=None)).days
            if delta <= 3:
                s += 0.1
            elif delta <= 7:
                s += 0.05

        title_len = len(item.title)
        if 10 <= title_len <= 50:
            s += 0.1

        return min(max(s, 0.0), 1.0)
