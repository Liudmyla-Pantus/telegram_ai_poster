from telethon import TelegramClient


def make_client(session: str, api_id: int, api_hash: str) -> TelegramClient:
    return TelegramClient(session, api_id, api_hash)
