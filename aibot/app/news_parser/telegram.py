from datetime import timezone

from telethon import TelegramClient

from .sites import ParsedNews


async def parse_telegram_channel(
    channel: str,
    source_name: str,
    api_id: int,
    api_hash: str,
    session: str,
    limit: int = 30,
    language: str | None = None,
) -> list[ParsedNews]:
    items: list[ParsedNews] = []
    async with TelegramClient(session, api_id, api_hash) as client:
        async for message in client.iter_messages(channel, limit=limit):
            text = (message.message or "").strip()
            if not text:
                continue
            title = text.splitlines()[0][:500]
            username = channel.lstrip("@")
            url = f"https://t.me/{username}/{message.id}" if username else None
            published = message.date.astimezone(timezone.utc)
            items.append(ParsedNews(title, url, text[:1000], source_name, published, text, language))
    return items
