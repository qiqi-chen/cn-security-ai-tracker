from typing import List

from models.company import Company
from models.news import ProcessedNewsItem, RawNewsItem
from core.processor.cleaner import Cleaner
from core.processor.deduplicator import Deduplicator
from core.processor.classifier import Classifier
from core.processor.scorer import Scorer
from utils.logger import get_logger

logger = get_logger(__name__)


class ProcessorPipeline:
    def __init__(
        self,
        cleaner: Cleaner,
        deduplicator: Deduplicator,
        classifier: Classifier,
        scorer: Scorer,
        companies: List[Company],
        min_content_length: int = 50,
        min_quality_score: float = 0.3,
    ):
        self._cleaner = cleaner
        self._deduplicator = deduplicator
        self._classifier = classifier
        self._scorer = scorer
        self._companies = companies
        self._min_content_length = min_content_length
        self._min_quality_score = min_quality_score

    def run(self, raw_items: List[RawNewsItem]) -> List[ProcessedNewsItem]:
        results = []
        for raw in raw_items:
            processed = self._process_one(raw)
            if processed:
                results.append(processed)
        logger.info("pipeline_done", input=len(raw_items), output=len(results))
        return results

    def _process_one(self, raw: RawNewsItem) -> ProcessedNewsItem | None:
        cleaned = self._cleaner.clean(raw)
        if len(cleaned) < self._min_content_length:
            return None
        if self._deduplicator.is_duplicate(raw):
            return None
        categories = self._classifier.classify(raw, cleaned)
        quality = self._scorer.score(raw, cleaned)
        if quality < self._min_quality_score:
            return None
        related = self._find_related_companies(raw.title + " " + cleaned)
        self._deduplicator.mark_seen(raw)
        return ProcessedNewsItem(
            raw=raw,
            cleaned_content=cleaned,
            related_companies=related,
            categories=categories,
            quality_score=quality,
            is_duplicate=False,
        )

    def _find_related_companies(self, text: str) -> List[str]:
        return [c.name for c in self._companies if any(n in text for n in c.all_names())]
