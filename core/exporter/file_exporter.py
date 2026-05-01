from pathlib import Path

from core.exporter.base import BaseExporter, ExportError
from models.report import Report


class FileExporter(BaseExporter):
    name = "markdown"

    def __init__(self, output_dir: str = "output/"):
        self._output_dir = Path(output_dir)

    def export(self, content: str, report: Report) -> str:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"ai_security_news_{report.generated_at.strftime('%Y%m%d_%H%M%S')}.md"
        path = self._output_dir / filename
        try:
            path.write_text(content, encoding="utf-8")
            return str(path.resolve())
        except OSError as e:
            raise ExportError(str(e)) from e
