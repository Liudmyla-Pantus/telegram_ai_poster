import asyncio
import logging
from datetime import datetime, timezone

from celery import Celery
from sqlalchemy import select

from .ai.generator import generate_post
from .api.schemas import NewsCreate
from .config import get_settings
from .database import SessionLocal
from .models import ErrorLog, NewsItem, Post, PostStatus, Source, SourceType
from .news_parser.sites import SiteParser
from .news_parser.telegram import parse_telegram_channel
from .services import save_news
from .telegram.publisher import publish_text

settings = get_settings()
celery_app = Celery("aibot", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    timezone="UTC",
    beat_schedule={"collect-news-every-30-minutes": {"task": "app.collect_all", "schedule": 1800.0}},
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)
logger = logging.getLogger(__name__)


def _log_error(db, operation: str, exc: Exception) -> None:
    db.add(ErrorLog(operation=operation, message=str(exc)))
    db.commit()


@celery_app.task(name="app.collect_source")
def collect_source(source_id: int) -> dict:
    with SessionLocal() as db:
        source = db.get(Source, source_id)
        if not source or not source.enabled:
            return {"source_id": source_id, "created": 0, "skipped": True}
        try:
            if source.type == SourceType.site:
                parsed = SiteParser(settings.request_timeout).parse(source.url, source.name, source.language)
            else:
                if not settings.telegram_api_id or not settings.telegram_api_hash:
                    raise ValueError("Для Telegram-джерела налаштуйте TELEGRAM_API_ID і TELEGRAM_API_HASH")
                parsed = asyncio.run(parse_telegram_channel(
                    source.url, source.name, settings.telegram_api_id, settings.telegram_api_hash,
                    settings.telegram_session, language=source.language,
                ))
            created_ids: list[str] = []
            for item in parsed:
                news, created = save_news(db, NewsCreate(**item.__dict__), source.id)
                if created:
                    created_ids.append(news.id)
            return {"source_id": source_id, "created": len(created_ids), "news_ids": created_ids}
        except Exception as exc:
            logger.exception("Source collection failed")
            _log_error(db, "collect_source", exc)
            return {"source_id": source_id, "created": 0, "error": str(exc)}


@celery_app.task(name="app.generate_post")
def generate_post_task(news_id: str) -> dict:
    with SessionLocal() as db:
        news = db.get(NewsItem, news_id)
        if not news:
            return {"error": "Новину не знайдено"}
        existing = db.scalar(select(Post).where(Post.news_id == news_id))
        if existing:
            return {"post_id": existing.id, "status": existing.status.value, "duplicate": True}
        try:
            text = generate_post(news.title, news.raw_text or news.summary, settings)
            post = Post(news_id=news.id, generated_text=text, status=PostStatus.generated)
            db.add(post)
            db.commit()
            db.refresh(post)
            return {"post_id": post.id, "status": post.status.value}
        except Exception as exc:
            post = Post(news_id=news.id, generated_text="", status=PostStatus.failed, error=str(exc))
            db.add(post)
            _log_error(db, "generate_post", exc)
            return {"post_id": post.id, "status": "failed", "error": str(exc)}


@celery_app.task(name="app.publish_post")
def publish_post_task(post_id: int, confirmed: bool = False) -> dict:
    with SessionLocal() as db:
        post = db.get(Post, post_id)
        if not post:
            return {"error": "Пост не знайдено"}
        if post.status == PostStatus.published:
            return {"post_id": post.id, "status": "published", "duplicate": True}
        if not confirmed:
            return {"post_id": post.id, "status": post.status.value, "error": "Потрібне явне підтвердження"}
        try:
            message_id = asyncio.run(publish_text(post.generated_text, settings))
            post.status = PostStatus.published
            post.published_at = datetime.now(timezone.utc)
            post.telegram_message_id = message_id
            db.commit()
            return {"post_id": post.id, "status": "published", "message_id": message_id}
        except Exception as exc:
            post.status = PostStatus.failed
            post.error = str(exc)
            _log_error(db, "publish_post", exc)
            return {"post_id": post.id, "status": "failed", "error": str(exc)}


@celery_app.task(name="app.collect_all")
def collect_all_task() -> dict:
    with SessionLocal() as db:
        source_ids = list(db.scalars(select(Source.id).where(Source.enabled.is_(True))))
    results = [collect_source(source_id) for source_id in source_ids]
    generated: list[dict] = []
    for result in results:
        for news_id in result.get("news_ids", []):
            with SessionLocal() as db:
                news = db.get(NewsItem, news_id)
                relevant = bool(news and news.is_relevant)
            if relevant:
                generation = generate_post_task(news_id)
                generated.append(generation)
                if settings.auto_publish and generation.get("post_id"):
                    publish_post_task(generation["post_id"], confirmed=True)
    return {"sources": len(source_ids), "collected": results, "generated": generated}
