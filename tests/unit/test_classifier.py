import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime
from models.news import RawNewsItem
from core.processor.classifier import Classifier


def _make_raw(title: str, content: str = "") -> RawNewsItem:
    return RawNewsItem(title=title, url="http://x.com", content=content,
                       source_name="test", source_type="rss", company_name="奇安信")


def test_product_release():
    raw = _make_raw("奇安信正式发布新版AI安全防护平台")
    cats = Classifier().classify(raw, "")
    assert "产品发布" in cats


def test_multiple_categories():
    raw = _make_raw("绿盟科技完成B轮融资，并发布新版AI安全产品")
    cats = Classifier().classify(raw, "")
    assert "融资并购" in cats
    assert "产品发布" in cats


def test_fallback_other():
    raw = _make_raw("今天天气很好")
    cats = Classifier().classify(raw, "")
    assert cats == ["其他"]


def test_security_event():
    raw = _make_raw("发现严重CVE漏洞影响多家厂商")
    cats = Classifier().classify(raw, "")
    assert "安全事件" in cats
