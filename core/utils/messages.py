from aiogram.types import Message

from core.text import split_message


async def send_lines(message: Message, header: str, lines: list[str]):
    """Answers with the header and the lines, in as many messages as Telegram's limit needs."""
    for part in split_message(header, lines):
        await message.answer(part, parse_mode="HTML", disable_web_page_preview=True)
