from abc import ABC, abstractmethod
from models.report import Report


class ExportError(Exception):
    pass


class BaseExporter(ABC):
    name: str = "base"

    @abstractmethod
    def export(self, content: str, report: Report) -> str:
        pass

    def is_available(self) -> bool:
        return True
