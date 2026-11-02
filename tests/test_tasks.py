from aibot.app.api.schemas import NewsCreate
from aibot.app.models import PostStatus
from aibot.app.services import save_news
import aibot.app.tasks as tasks


def test_generate_celery_task(db_session, monkeypatch):
    news, _ = save_news(db_session, NewsCreate(
        title="Celery тест", summary="Перевірка фонової генерації", source="pytest"
    ))
    factory = lambda: db_session  # noqa: E731
    monkeypatch.setattr(tasks, "SessionLocal", factory)
    result = tasks.generate_post_task.run(news.id)
    assert result["status"] == PostStatus.generated.value
    assert result["post_id"]


def test_collect_all_without_sources(db_session, monkeypatch):
    factory = lambda: db_session  # noqa: E731
    monkeypatch.setattr(tasks, "SessionLocal", factory)
    result = tasks.collect_all_task.run()
    assert result == {"sources": 0, "collected": [], "generated": []}
