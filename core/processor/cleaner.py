import re
from bs4 import BeautifulSoup
from models.news import RawNewsItem

_NOISE_PATTERNS = [
    r"版权所有.*$", r"扫码关注.*$", r"阅读原文.*$",
    r"点击查看.*$", r"相关推荐.*$", r"猜你喜欢.*$",
    r"责任编辑.*$", r"来源：.*$", r"编辑：.*$", r"本文.*转载.*$",
]
_COMPILED = [re.compile(p, re.MULTILINE) for p in _NOISE_PATTERNS]


class Cleaner:
    def clean(self, raw: RawNewsItem) -> str:
        text = raw.content
        if "<" in text and ">" in text:
            soup = BeautifulSoup(text, "lxml")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n")
        for pattern in _COMPILED:
            text = pattern.sub("", text)
        lines = [line.strip() for line in text.splitlines()]
        result_lines: list[str] = []
        blank_count = 0
        for line in lines:
            if not line:
                blank_count += 1
                if blank_count <= 1:
                    result_lines.append("")
            else:
                blank_count = 0
                result_lines.append(line)
        return "\n".join(result_lines).strip()
