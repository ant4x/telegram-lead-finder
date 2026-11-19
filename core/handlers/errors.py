"""
Errors the bot expects. A quick second tap on a button arrives before the first one has redrawn the message,
so Telegram refuses the second edit as changing nothing; without an answer the button keeps spinning.
"""
from aiogram.filters import ExceptionMessageFilter
from aiogram.types import ErrorEvent

UNCHANGED = ExceptionMessageFilter(r".*message is not modified")


async def unchanged_message(event: ErrorEvent):
    """The tap is answered and the error dropped: the message already shows what the tap asked for."""
    if event.update.callback_query:
        await event.update.callback_query.answer()
