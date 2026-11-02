from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .api.schemas import NewsCreate
from .filters import is_relevant
from .models import NewsItem
from .utils import news_fingerprint, normalize_text


def save_news(db: Session, data: NewsCreate, source_id: int | None = None) -> tuple[NewsItem, bool]:
    fingerprint = news_fingerprint(data.title, data.url, data.raw_text or data.summary)
    normalized_title = normalize_text(data.title)
    duplicate = db.scalar(
        select(NewsItem).where(
            or_(
                NewsItem.fingerprint == fingerprint,
                NewsItem.url == data.url if data.url else NewsItem.fingerprint == fingerprint,
            )
        )
    )
    same_source_items = db.scalars(select(NewsItem).where(NewsItem.source == data.source)).all()
    duplicate_by_title = next(
        (item for item in same_source_items if normalize_text(item.title) == normalized_title), None
    )
    if duplicate or duplicate_by_title:
        return duplicate or duplicate_by_title, False
    news = NewsItem(
        **data.model_dump(exclude={"published_at"}),
        published_at=data.published_at or datetime.now(timezone.utc),
        source_id=source_id,
        fingerprint=fingerprint,
    )
    db.add(news)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(NewsItem).where(NewsItem.fingerprint == fingerprint))
        return existing, False
    news.is_relevant = is_relevant(news, db)
    db.commit()
    db.refresh(news)
    return news, True
