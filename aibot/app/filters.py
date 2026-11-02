from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import Keyword, NewsItem
from .utils import normalize_text


def _keyword_matches(keyword: str, text: str) -> bool:
    normalized = normalize_text(keyword)
    if normalized in text:
        return True
    # Lightweight inflection tolerance for Ukrainian without an NLP dependency:
    # compare stems of meaningful words (e.g. "штучний" / "штучного").
    haystack_stems = {word[:5] for word in text.split() if len(word) >= 5}
    keyword_stems = {word[:5] for word in normalized.split() if len(word) >= 5}
    return bool(keyword_stems) and keyword_stems.issubset(haystack_stems)


def is_relevant(news: NewsItem, db: Session) -> bool:
    expected_language = get_settings().default_language
    if expected_language and news.language and news.language.lower() != expected_language.lower():
        return False
    # Read all rows and evaluate the flag in Python as well. This is predictable
    # for newly-created rows in the same transaction and across SQLite/Postgres.
    words = [item for item in db.scalars(select(Keyword)).all() if item.enabled]
    if not words:
        return True
    haystack = normalize_text(" ".join((news.title, news.summary, news.raw_text or "")))
    return any(_keyword_matches(keyword.word, haystack) for keyword in words)
