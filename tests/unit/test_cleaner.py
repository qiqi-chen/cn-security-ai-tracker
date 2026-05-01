import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime
from models.news import RawNewsItem
from core.processor.cleaner import Cleaner


def _make_raw(content: str) -> RawNewsItem:
    return RawNewsItem(title="测试", url="http://x.com", content=content,
                       source_name="test", source_type="rss", company_name="奇安信")


def test_strips_html():
    raw = _make_raw("<p>正文内容</p><script>alert(1)</script>")
    result = Cleaner().clean(raw)
    assert "<p>" not in result
    assert "正文内容" in result


def test_removes_noise_patterns():
    raw = _make_raw("正文内容\n版权所有 奇安信科技\n相关推荐：xxx")
    result = Cleaner().clean(raw)
    assert "版权所有" not in result
    assert "正文内容" in result


def test_collapses_blank_lines():
    raw = _make_raw("第一行\n\n\n\n第二行")
    result = Cleaner().clean(raw)
    assert "\n\n\n" not in result


def test_plain_text_passthrough():
    raw = _make_raw("这是一段普通的新闻正文，包含AI安全相关内容。")
    result = Cleaner().clean(raw)
    assert "这是一段普通的新闻正文" in result
