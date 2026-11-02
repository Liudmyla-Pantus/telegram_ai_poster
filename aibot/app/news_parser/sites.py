from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


@dataclass
class ParsedNews:
    title: str
    url: str | None
    summary: str
    source: str
    published_at: datetime
    raw_text: str | None = None
    language: str | None = None


class SiteParser:
    """Generic semantic HTML parser suitable for common news listing pages."""

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def parse(self, url: str, source_name: str, language: str | None = None) -> list[ParsedNews]:
        response = requests.get(
            url,
            timeout=self.timeout,
            headers={"User-Agent": "M4-AI-News-Poster/1.0 (educational project)"},
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        items: list[ParsedNews] = []
        seen: set[str] = set()
        containers = soup.select("article") or soup.select("main li")
        for container in containers[:50]:
            link = container.select_one("h1 a, h2 a, h3 a, a[href]")
            heading = container.select_one("h1, h2, h3")
            title = (heading or link).get_text(" ", strip=True) if (heading or link) else ""
            href = urljoin(url, link.get("href", "")) if link else None
            summary_node = container.select_one("p")
            summary = summary_node.get_text(" ", strip=True) if summary_node else title
            if len(title) < 3 or title.lower() in seen:
                continue
            seen.add(title.lower())
            items.append(ParsedNews(title, href, summary, source_name, datetime.now(timezone.utc), language=language))
        return items
