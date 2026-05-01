import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from datetime import datetime
from models.news import RawNewsItem
from core.processor.deduplicator import Deduplicator


def _make_raw(url: str, content: str = "default content") -> RawNewsItem:
    return RawNewsItem(title="标题", url=url, content=content,
                       source_name="test", source_type="rss", company_name="奇安信")


@pytest.fixture
def dedup(tmp_path):
    db = tmp_path / "test_cache.db"
    d = Deduplicator(db_path=str(db), retention_days=90)
    yield d
    d.close()


def test_new_item_not_duplicate(dedup):
    item = _make_raw("http://new.com/1")
    assert not dedup.is_duplicate(item)


def test_seen_url_is_duplicate(dedup):
    item = _make_raw("http://dup.com/1")
    dedup.mark_seen(item)
    assert dedup.is_duplicate(item)


def test_same_content_different_url_is_duplicate(dedup):
    item1 = _make_raw("http://site-a.com/news", content="同一篇内容的文章正文")
    item2 = _make_raw("http://site-b.com/news", content="同一篇内容的文章正文")
    dedup.mark_seen(item1)
    assert dedup.is_duplicate(item2)


def test_different_content_not_duplicate(dedup):
    item1 = _make_raw("http://site-a.com/1", content="第一篇文章的内容")
    item2 = _make_raw("http://site-b.com/2", content="第二篇完全不同的文章内容")
    dedup.mark_seen(item1)
    assert not dedup.is_duplicate(item2)
