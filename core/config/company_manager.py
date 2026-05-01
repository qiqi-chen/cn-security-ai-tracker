from pathlib import Path
from typing import List, Optional
import yaml
from models.company import Company


class CompanyManager:
    def __init__(self):
        self._companies: List[Company] = []

    def load(self, path: str = "config/companies.yaml") -> List[Company]:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        self._companies = [
            Company(
                name=c["name"],
                english_name=c.get("english_name", ""),
                aliases=c.get("aliases", []),
                product=c.get("product", ""),
                partner=c.get("partner", ""),
                website=c.get("website", ""),
                news_url=c.get("news_url", ""),
                news_article_selector=c.get("news_article_selector", ""),
                news_title_selector=c.get("news_title_selector", "h2"),
                news_link_selector=c.get("news_link_selector", "a"),
            )
            for c in data.get("companies", [])
        ]
        return self._companies

    def get_all(self) -> List[Company]:
        return self._companies

    def get_by_name(self, name: str) -> Optional[Company]:
        for c in self._companies:
            if name in c.all_names():
                return c
        return None

    def save(self, companies: List[Company], path: str) -> None:
        data = {
            "companies": [
                {
                    "name": c.name,
                    "english_name": c.english_name,
                    "aliases": c.aliases,
                    "product": c.product,
                    "partner": c.partner,
                    "website": c.website,
                }
                for c in companies
            ]
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
