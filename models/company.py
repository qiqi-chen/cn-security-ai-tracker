from dataclasses import dataclass, field
from typing import List

@dataclass
class Company:
    name: str
    english_name: str
    aliases: List[str] = field(default_factory=list)
    product: str = ""
    partner: str = ""
    website: str = ""
    news_url: str = ""
    news_article_selector: str = ""
    news_title_selector: str = "h2"
    news_link_selector: str = "a"
    news_count: int = 0

    def all_names(self) -> List[str]:
        names = [self.name, self.english_name] + self.aliases
        return list(dict.fromkeys(n for n in names if n))
