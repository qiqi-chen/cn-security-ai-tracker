import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime, timedelta
from models.news import RawNewsItem
from core.processor.scorer import Scorer


def _make_raw(title: str = "测试标题奇安信AI安全", source: str = "test",
              published_at=None) -> RawNewsItem:
    return RawNewsItem(title=title, url="http://x.com", content="",
                       source_name=source, source_type="rss",
                       company_name="奇安信", published_at=published_at)


def test_base_score():
    score = Scorer().score(_make_raw(), "")
    assert 0.0 <= score <= 1.0


def test_long_content_higher_score():
    short_score = Scorer().score(_make_raw(), "短" * 10)
    long_score = Scorer().score(_make_raw(), "长" * 200)
    assert long_score > short_score


def test_trusted_source_bonus():
    normal = Scorer().score(_make_raw(source="unknown"), "内容" * 50)
    trusted = Scorer().score(_make_raw(source="安全客"), "内容" * 50)
    assert trusted > normal


def test_recent_news_bonus():
    old = _make_raw(published_at=datetime.now() - timedelta(days=30))
    fresh = _make_raw(published_at=datetime.now() - timedelta(days=1))
    old_score = Scorer().score(old, "内容" * 50)
    fresh_score = Scorer().score(fresh, "内容" * 50)
    assert fresh_score > old_score


def test_score_clamped():
    item = _make_raw(title="奇安信发布新AI产品", source="安全客",
                     published_at=datetime.now())
    score = Scorer().score(item, "详细内容" * 200)
    assert 0.0 <= score <= 1.0
