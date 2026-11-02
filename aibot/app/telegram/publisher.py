from ..config import Settings
from .bot import make_client


async def publish_text(text: str, settings: Settings) -> int:
    if settings.test_mode:
        raise RuntimeError("Публікацію заблоковано: TEST_MODE=true")
    if not all((settings.telegram_api_id, settings.telegram_api_hash, settings.telegram_target_channel)):
        raise ValueError("Не налаштовано TELEGRAM_API_ID, TELEGRAM_API_HASH або TELEGRAM_TARGET_CHANNEL")
    async with make_client(settings.telegram_session, settings.telegram_api_id, settings.telegram_api_hash) as client:
        message = await client.send_message(settings.telegram_target_channel, text)
        return message.id
