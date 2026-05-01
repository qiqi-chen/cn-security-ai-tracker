import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from core.enhancer.llm_client import DeepSeekClient, LLMError
from core.enhancer.cache import LLMCache
from models.news import ProcessedNewsItem
from utils.logger import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """你是一位中文网络安全行业分析师，请为以下新闻生成摘要和关键点。

要求：
- 摘要：100字以内，中文，客观描述核心内容
- 关键点：3-5条，每条不超过20字，以列表形式返回
- 仅输出 JSON，格式：{"summary": "...", "key_points": ["...", "..."]}"""


class Summarizer:
    def __init__(self, client: DeepSeekClient, cache: LLMCache, concurrency: int = 5):
        self._client = client
        self._cache = cache
        self._concurrency = concurrency
        self._llm_available: bool | None = None

    def enrich_batch(self, items: List[ProcessedNewsItem]) -> List[ProcessedNewsItem]:
        if self._llm_available is None:
            self._llm_available = self._client.is_available()
            if not self._llm_available:
                logger.warning("llm_unavailable_fallback_mode")

        needs_llm = []
        for item in items:
            cached = self._cache.get(item.raw.content_hash)
            if cached:
                item.summary = cached["summary"]
                item.key_points = cached["key_points"]
            elif self._llm_available:
                needs_llm.append(item)
            else:
                item.summary = self._fallback_summary(item)
                item.key_points = []

        if needs_llm:
            self._process_with_llm(needs_llm)

        return items

    def _process_with_llm(self, items: List[ProcessedNewsItem]) -> None:
        with ThreadPoolExecutor(max_workers=self._concurrency) as executor:
            futures = {executor.submit(self._enrich_one, item): item for item in items}
            for future in as_completed(futures):
                item = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.warning("llm_enrich_error", title=item.title[:50], error=str(e))
                    item.summary = self._fallback_summary(item)
                    item.key_points = []

    def _enrich_one(self, item: ProcessedNewsItem) -> None:
        user_prompt = f"标题：{item.title}\n正文：{item.cleaned_content[:1500]}"
        try:
            raw = self._client.chat(_SYSTEM_PROMPT, user_prompt).strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = json.loads(raw)
            item.summary = parsed.get("summary", "")
            item.key_points = parsed.get("key_points", [])
        except (LLMError, json.JSONDecodeError) as e:
            logger.warning("llm_parse_error", error=str(e))
            item.summary = self._fallback_summary(item)
            item.key_points = []
        self._cache.set(item.raw.content_hash, item.summary, item.key_points)

    def _fallback_summary(self, item: ProcessedNewsItem) -> str:
        text = item.cleaned_content or item.title
        return text[:150].rstrip() + ("..." if len(text) > 150 else "")
