from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..ai.generator import generate_post
from ..config import get_settings
from ..database import get_db
from ..models import ErrorLog, Keyword, NewsItem, Post, Source
from ..services import save_news
from ..tasks import collect_all_task, generate_post_task, publish_post_task
from .schemas import (
    ErrorLogRead, GenerateRequest, KeywordCreate, KeywordRead, KeywordUpdate, NewsCreate,
    NewsRead, PostRead, PublishRequest, SourceCreate, SourceRead, SourceUpdate,
)

router = APIRouter(prefix="/api")


def _commit_or_409(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Запис із таким унікальним значенням уже існує") from exc


@router.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "test_mode": get_settings().test_mode}


@router.post("/sources/", response_model=SourceRead, status_code=201, tags=["sources"])
def create_source(payload: SourceCreate, db: Session = Depends(get_db)):
    item = Source(**payload.model_dump())
    db.add(item); _commit_or_409(db); db.refresh(item)
    return item


@router.get("/sources/", response_model=list[SourceRead], tags=["sources"])
def list_sources(db: Session = Depends(get_db)):
    return db.scalars(select(Source).order_by(Source.id)).all()


@router.get("/sources/{item_id}", response_model=SourceRead, tags=["sources"])
def get_source(item_id: int, db: Session = Depends(get_db)):
    if not (item := db.get(Source, item_id)): raise HTTPException(404, "Джерело не знайдено")
    return item


@router.patch("/sources/{item_id}", response_model=SourceRead, tags=["sources"])
def update_source(item_id: int, payload: SourceUpdate, db: Session = Depends(get_db)):
    if not (item := db.get(Source, item_id)): raise HTTPException(404, "Джерело не знайдено")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    _commit_or_409(db); db.refresh(item); return item


@router.delete("/sources/{item_id}", status_code=204, tags=["sources"])
def delete_source(item_id: int, db: Session = Depends(get_db)):
    if not (item := db.get(Source, item_id)): raise HTTPException(404, "Джерело не знайдено")
    db.delete(item); db.commit()


@router.post("/keywords/", response_model=KeywordRead, status_code=201, tags=["keywords"])
def create_keyword(payload: KeywordCreate, db: Session = Depends(get_db)):
    item = Keyword(**payload.model_dump()); db.add(item); _commit_or_409(db); db.refresh(item); return item


@router.get("/keywords/", response_model=list[KeywordRead], tags=["keywords"])
def list_keywords(db: Session = Depends(get_db)):
    return db.scalars(select(Keyword).order_by(Keyword.id)).all()


@router.patch("/keywords/{item_id}", response_model=KeywordRead, tags=["keywords"])
def update_keyword(item_id: int, payload: KeywordUpdate, db: Session = Depends(get_db)):
    if not (item := db.get(Keyword, item_id)): raise HTTPException(404, "Ключове слово не знайдено")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    _commit_or_409(db); db.refresh(item); return item


@router.delete("/keywords/{item_id}", status_code=204, tags=["keywords"])
def delete_keyword(item_id: int, db: Session = Depends(get_db)):
    if not (item := db.get(Keyword, item_id)): raise HTTPException(404, "Ключове слово не знайдено")
    db.delete(item); db.commit()


@router.post("/news/", response_model=NewsRead, status_code=201, tags=["news"])
def create_news(payload: NewsCreate, db: Session = Depends(get_db)):
    item, created = save_news(db, payload)
    if not created: raise HTTPException(409, detail={"message": "Дублікат новини", "news_id": item.id})
    return item


@router.get("/news/", response_model=list[NewsRead], tags=["news"])
def list_news(relevant: bool | None = None, limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    stmt = select(NewsItem).order_by(NewsItem.published_at.desc()).limit(limit)
    if relevant is not None: stmt = stmt.where(NewsItem.is_relevant == relevant)
    return db.scalars(stmt).all()


@router.get("/news/{news_id}", response_model=NewsRead, tags=["news"])
def get_news(news_id: str, db: Session = Depends(get_db)):
    if not (item := db.get(NewsItem, news_id)): raise HTTPException(404, "Новину не знайдено")
    return item


@router.delete("/news/{news_id}", status_code=204, tags=["news"])
def delete_news(news_id: str, db: Session = Depends(get_db)):
    if not (item := db.get(NewsItem, news_id)):
        raise HTTPException(404, "Новину не знайдено")
    db.delete(item)
    db.commit()


@router.post("/generate/", tags=["generation"])
def manual_generate(payload: GenerateRequest, db: Session = Depends(get_db)):
    if payload.news_id:
        if not db.get(NewsItem, payload.news_id): raise HTTPException(404, "Новину не знайдено")
        return generate_post_task(payload.news_id)
    if not payload.text: raise HTTPException(422, "Передайте news_id або text")
    return {"generated_text": generate_post(payload.title or "Новина", payload.text, get_settings()), "test_mode": get_settings().test_mode}


@router.get("/posts/", response_model=list[PostRead], tags=["posts"])
def list_posts(db: Session = Depends(get_db)):
    return db.scalars(select(Post).order_by(Post.created_at.desc())).all()


@router.get("/posts/{post_id}", response_model=PostRead, tags=["posts"])
def get_post(post_id: int, db: Session = Depends(get_db)):
    if not (item := db.get(Post, post_id)):
        raise HTTPException(404, "Пост не знайдено")
    return item


@router.post("/posts/{post_id}/publish", tags=["posts"])
def publish_post(post_id: int, payload: PublishRequest, db: Session = Depends(get_db)):
    if not db.get(Post, post_id): raise HTTPException(404, "Пост не знайдено")
    result = publish_post_task(post_id, payload.confirm)
    if "error" in result: raise HTTPException(status.HTTP_409_CONFLICT, result)
    return result


@router.post("/collect/", status_code=202, tags=["collection"])
def collect_manually():
    task = collect_all_task.delay()
    return {"task_id": task.id, "status": "queued"}


@router.get("/errors/", response_model=list[ErrorLogRead], tags=["system"])
def list_errors(db: Session = Depends(get_db)):
    return db.scalars(select(ErrorLog).order_by(ErrorLog.created_at.desc()).limit(100)).all()
