#!/usr/bin/env python3
import argparse
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config.config_manager import ConfigManager
from core.config.company_manager import CompanyManager
from core.collector.rss_source import RSSSource
from core.collector.company_website import CompanyWebsiteSource, WebsiteConfig
from core.collector.playwright_source import PlaywrightSource
from core.collector.aggregator import Aggregator
from core.processor.cleaner import Cleaner
from core.processor.deduplicator import Deduplicator
from core.processor.classifier import Classifier
from core.processor.scorer import Scorer
from core.processor.pipeline import ProcessorPipeline
from core.enhancer.llm_client import DeepSeekClient
from core.enhancer.cache import LLMCache
from core.enhancer.summarizer import Summarizer
from core.analyzer.statistics import StatisticsCalculator
from core.analyzer.trend_analyzer import TrendAnalyzer
from core.reporter.markdown_reporter import MarkdownReporter
from core.exporter.file_exporter import FileExporter
from core.exporter.feishu_exporter import FeishuExporter
from core.exporter.dingtalk_exporter import DingtalkExporter
from core.exporter.base import BaseExporter, ExportError
from models.report import Report
from utils.logger import setup_logging, get_logger

logger = get_logger(__name__)

_TIME_RANGE_DAYS = {"week": 7, "month": 30, "year": 365}


def run(params: dict | None = None) -> dict:
    params = params or {}
    start_ts = time.time()
    errors: List[str] = []

    config_path = params.get("config_path", "config/config.yaml")
    cfg = ConfigManager.get_instance(config_path)

    log_level = "DEBUG" if params.get("verbose") else cfg.get("logging.level", "INFO")
    log_fmt = cfg.get("logging.format", "json")
    setup_logging(log_level, log_fmt)

    company_mgr = CompanyManager()
    all_companies = company_mgr.load("config/companies.yaml")
    filter_names = params.get("companies", [])
    companies = [c for c in all_companies if c.name in filter_names] if filter_names else all_companies

    time_range = params.get("time_range") or cfg.get("collector.time_range", "month")
    days = _TIME_RANGE_DAYS.get(time_range, 30)
    period_end = datetime.now()
    period_start = period_end - timedelta(days=days)

    sources = _build_sources(cfg, companies)
    aggregator = Aggregator(sources, concurrency=cfg.get("collector.concurrency", 8))

    logger.info("collection_start", companies=len(companies), time_range=time_range)
    raw_items = aggregator.collect_all(companies, period_start)
    logger.info("collection_done", total_raw=len(raw_items))

    pipeline = ProcessorPipeline(
        cleaner=Cleaner(),
        deduplicator=Deduplicator(
            db_path=cfg.get("processor.dedup_db_path", "data/cache/news_cache.db"),
            retention_days=cfg.get("processor.dedup_retention_days", 90),
        ),
        classifier=Classifier(),
        scorer=Scorer(),
        companies=companies,
        min_content_length=cfg.get("processor.min_content_length", 50),
        min_quality_score=cfg.get("processor.min_quality_score", 0.3),
    )
    processed = pipeline.run(raw_items)
    logger.info("processing_done", total_processed=len(processed))

    if not params.get("no_llm") and cfg.get("enhancer.enabled", True):
        llm_client = DeepSeekClient(
            base_url=cfg.get("enhancer.base_url", "https://api.deepseek.com"),
            model=cfg.get("enhancer.model", "deepseek-chat"),
            max_tokens=cfg.get("enhancer.max_tokens", 300),
            temperature=cfg.get("enhancer.temperature", 0.3),
        )
        llm_cache = LLMCache(cfg.get("enhancer.cache_db_path", "data/cache/llm_cache.db"))
        summarizer = Summarizer(llm_client, llm_cache, cfg.get("enhancer.concurrency", 5))
        processed = summarizer.enrich_batch(processed)

    stats_calc = StatisticsCalculator()
    stats = stats_calc.compute(processed, companies)

    trend_analyzer = TrendAnalyzer(
        window_days=cfg.get("analyzer.trend_window_days", 7),
        threshold=cfg.get("analyzer.trend_threshold", 0.5),
        top_keywords_count=cfg.get("analyzer.top_keywords_count", 20),
    )
    analysis = trend_analyzer.analyze(processed, companies, stats)

    report = Report(
        title=f"中国网络安全厂商 AI 动态报告（{period_start.strftime('%Y.%m.%d')}–{period_end.strftime('%m.%d')}）",
        period_start=period_start,
        period_end=period_end,
        companies=companies,
        news_items=processed,
        analysis=analysis,
        total_companies_monitored=len(companies),
        total_news_collected=len(processed),
        active_companies_count=stats.get("active_companies", 0),
    )

    reporter = MarkdownReporter(
        max_news_per_company=cfg.get("reporter.max_news_per_company", 5),
        sort_by=cfg.get("reporter.sort_by", "quality"),
        include_empty_companies=cfg.get("reporter.include_empty_companies", False),
    )
    content = reporter.generate(report)

    output_paths: List[str] = []
    if not params.get("dry_run"):
        exporters = _build_exporters(cfg, params)
        for exporter in exporters:
            if not exporter.is_available():
                logger.warning("exporter_unavailable", name=exporter.name)
                errors.append(f"{exporter.name} 不可用，已跳过")
                continue
            try:
                result = exporter.export(content, report)
                output_paths.append(result)
                logger.info("export_success", name=exporter.name, result=result)
            except ExportError as e:
                logger.error("export_failed", name=exporter.name, error=str(e))
                errors.append(f"{exporter.name} 导出失败: {e}")
    else:
        logger.info("dry_run_mode_skip_export")

    duration = round(time.time() - start_ts, 2)
    status = "success" if not errors else ("partial" if output_paths else "error")

    return {
        "status": status,
        "output_paths": output_paths,
        "companies_monitored": len(companies),
        "news_collected": len(raw_items),
        "news_after_dedup": len(processed),
        "active_companies": stats.get("active_companies", 0),
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "duration_seconds": duration,
        "errors": errors,
    }


def _build_sources(cfg, companies=None):
    sources = []
    if cfg.get("sources.rss.enabled", True):
        feeds = cfg.get("sources.rss.feeds", [])
        sources.append(RSSSource(feeds=feeds, timeout=cfg.get("collector.timeout", 10)))
    if cfg.get("sources.company_website.enabled", True):
        website_configs = {}
        for company in (companies or []):
            if company.news_url and company.news_article_selector:
                website_configs[company.name] = WebsiteConfig(
                    url=company.news_url,
                    article_selector=company.news_article_selector,
                    title_selector=company.news_title_selector,
                    link_selector=company.news_link_selector,
                )
        sources.append(CompanyWebsiteSource(configs=website_configs))
    if cfg.get("sources.playwright.enabled", False):
        sources.append(PlaywrightSource())
    return sources


def _build_exporters(cfg, params) -> List[BaseExporter]:
    targets = params.get("format") or cfg.get("exporter.targets", ["markdown"])
    if targets == "all":
        targets = ["markdown", "feishu", "dingtalk"]
    if isinstance(targets, str):
        targets = [targets]
    exporters: List[BaseExporter] = []
    if "markdown" in targets or not targets:
        exporters.append(FileExporter(output_dir=cfg.get("exporter.output_dir", "output/")))
    if "feishu" in targets and cfg.get("exporter.feishu.enabled", False):
        exporters.append(FeishuExporter(
            cli_bin=cfg.get("exporter.feishu.cli_bin", "feishu"),
            folder_token=cfg.get("exporter.feishu.folder_token", ""),
            notify_webhook=cfg.get("exporter.feishu.notify_webhook", ""),
        ))
    if "dingtalk" in targets and cfg.get("exporter.dingtalk.enabled", False):
        exporters.append(DingtalkExporter(
            cli_bin=cfg.get("exporter.dingtalk.cli_bin", "dingtalk"),
            notify_webhook=cfg.get("exporter.dingtalk.notify_webhook", ""),
            doc_space_id=cfg.get("exporter.dingtalk.doc_space_id", ""),
        ))
    if not exporters:
        exporters.append(FileExporter(output_dir=cfg.get("exporter.output_dir", "output/")))
    return exporters


def _parse_args() -> dict:
    parser = argparse.ArgumentParser(description="中国网络安全 AI 动态追踪系统")
    parser.add_argument("--time-range", choices=["week", "month", "year"], default=None)
    parser.add_argument("--format", action="append", dest="format", default=None,
                        choices=["markdown", "feishu", "dingtalk", "all"])
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--company", action="append", dest="companies", default=[])
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--config", dest="config_path", default="config/config.yaml")
    parser.add_argument("--discover-companies", action="store_true")
    args = parser.parse_args()
    return {
        "time_range": args.time_range,
        "format": args.format,
        "no_llm": args.no_llm,
        "dry_run": args.dry_run,
        "companies": args.companies,
        "verbose": args.verbose,
        "config_path": args.config_path,
        "discover_companies": args.discover_companies,
    }


if __name__ == "__main__":
    params = _parse_args()
    result = run(params)
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["status"] in ("success", "partial") else 1)
