from aiogram.types import Message

from core.commands import start_text
from core.settings import settings


async def start(message: Message):
    await message.answer(start_text(message.from_user.first_name or "there", settings.modules), parse_mode="HTML")


async def admins_only(message: Message):
    await message.answer("❌ Only admins can use this command.")


async def filter_text(message: Message):
    await message.answer("⚠️ I only understand commands. Send /start to see the list.")
