from abc import ABC, abstractmethod
from datetime import datetime
from typing import List
from models.company import Company
from models.news import RawNewsItem


class BaseSource(ABC):
    name: str = "base"

    @abstractmethod
    def fetch(self, company: Company, start_date: datetime) -> List[RawNewsItem]:
        pass

    def is_available(self) -> bool:
        return True
