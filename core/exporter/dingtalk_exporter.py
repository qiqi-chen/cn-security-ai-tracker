import shutil
import subprocess
import tempfile
from pathlib import Path

from core.exporter.base import BaseExporter, ExportError
from models.report import Report
from utils.logger import get_logger

logger = get_logger(__name__)

_CLI_TIMEOUT = 30


class DingtalkExporter(BaseExporter):
    name = "dingtalk"

    def __init__(self, cli_bin: str = "dingtalk", notify_webhook: str = "", doc_space_id: str = ""):
        self._cli_bin = cli_bin
        self._notify_webhook = notify_webhook
        self._doc_space_id = doc_space_id

    def is_available(self) -> bool:
        return shutil.which(self._cli_bin) is not None

    def export(self, content: str, report: Report) -> str:
        doc_url = ""

        if self._doc_space_id:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, encoding="utf-8",
                prefix=f"report_{report.generated_at.strftime('%Y%m%d_%H%M%S')}_"
            ) as f:
                f.write(content)
                tmp_path = f.name
            try:
                doc_url = self._create_doc(tmp_path, report.title)
            finally:
                Path(tmp_path).unlink(missing_ok=True)

        if self._notify_webhook:
            self._send_message(doc_url, report)

        return doc_url or "dingtalk:message_sent"

    def _create_doc(self, file_path: str, title: str) -> str:
        # TODO: 替换为实际钉钉 CLI 的文档创建命令
        cmd = [self._cli_bin, "doc", "create",
               "--space", self._doc_space_id,
               "--file", file_path,
               "--title", title]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=_CLI_TIMEOUT)
        if result.returncode != 0:
            raise ExportError(f"钉钉 CLI 执行失败: {result.stderr}")
        return result.stdout.strip() or "dingtalk:doc_created"

    def _send_message(self, doc_url: str, report: Report) -> None:
        # TODO: 替换为实际钉钉 CLI 的消息发送命令
        summary = self._build_summary(report, doc_url)
        cmd = [self._cli_bin, "message", "send",
               "--webhook", self._notify_webhook,
               "--markdown", summary]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=_CLI_TIMEOUT)
        if result.returncode != 0:
            logger.warning("dingtalk_message_failed", error=result.stderr)

    def _build_summary(self, report: Report, doc_url: str) -> str:
        lines = [
            f"## {report.title}",
            f"本期新闻：{report.total_news_collected} 条",
            f"活跃厂商：{report.active_companies_count} 家",
        ]
        if report.analysis and report.analysis.trends:
            lines.append(f"核心趋势：{report.analysis.trends[0]}")
        if doc_url:
            lines.append(f"[查看完整报告]({doc_url})")
        return "\n".join(lines)
