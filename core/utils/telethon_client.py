from telethon import TelegramClient
from core.settings import settings


client = TelegramClient(
    'my_monitor_session',
    settings.telethon.api_id,
    settings.telethon.api_hash
)