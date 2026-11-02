from .openai_client import request_completion
from ..config import Settings


def build_prompt(title: str, text: str) -> str:
    return f"""Ти — редактор українського Telegram-каналу.
На основі новини створи готовий пост українською мовою.
Вимоги: короткий виразний заголовок, 2–4 лаконічні абзаци, доречні емодзі,
фактичність без вигадок і завершальний call to action. Не додавай пояснень поза постом.

Заголовок джерела: {title}
Текст новини: {text}
"""


def generate_post(title: str, text: str, settings: Settings) -> str:
    if settings.test_mode:
        clean = " ".join(text.split())
        return f"📰 {title}\n\n{clean[:500]}\n\n👉 Що ви думаєте про цю новину?"
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY не налаштовано")
    return request_completion(settings.openai_api_key, settings.openai_model, build_prompt(title, text))
