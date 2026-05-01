import shutil
import subprocess
import tempfile
from pathlib import Path

from core.exporter.base import BaseExporter, ExportError
from models.report import Report
from utils.logger import get_logger

logger = get_logger(__name__)

_CLI_TIMEOUT = 30


class FeishuExporter(BaseExporter):
    name = "feishu"

    def __init__(self, cli_bin: str = "feishu", folder_token: str = "", notify_webhook: str = ""):
        self._cli_bin = cli_bin
        self._folder_token = folder_token
        self._notify_webhook = notify_webhook

    def is_available(self) -> bool:
        return shutil.which(self._cli_bin) is not None

    def export(self, content: str, report: Report) -> str:
        # TODO: 替换为真实的飞书 CLI 命令格式
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8",
            prefix=f"report_{report.generated_at.strftime('%Y%m%d_%H%M%S')}_"
        ) as f:
            f.write(content)
            tmp_path = f.name

        try:
            doc_url = self._create_doc(tmp_path, report.title)
            if self._notify_webhook:
                self._send_message(doc_url, report)
            return doc_url
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _create_doc(self, file_path: str, title: str) -> str:
        # TODO: 替换为实际飞书 CLI 的文档创建命令
        cmd = [self._cli_bin, "doc", "create",
               "--folder", self._folder_token,
               "--file", file_path,
               "--title", title]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=_CLI_TIMEOUT)
        if result.returncode != 0:
            raise ExportError(f"飞书 CLI 执行失败: {result.stderr}")
        return result.stdout.strip() or "feishu:doc_created"

    def _send_message(self, doc_url: str, report: Report) -> None:
        # TODO: 替换为实际飞书 CLI 的消息发送命令
        summary = f"📊 {report.title}\n本期新闻：{report.total_news_collected} 条\n报告链接：{doc_url}"
        cmd = [self._cli_bin, "webhook", "send",
               "--url", self._notify_webhook,
               "--text", summary]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=_CLI_TIMEOUT)
        if result.returncode != 0:
            logger.warning("feishu_message_failed", error=result.stderr)
