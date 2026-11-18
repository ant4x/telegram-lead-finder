from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def join_keyboard(join_data: str) -> InlineKeyboardMarkup:
    """Yes lets the reading account join the channels the message names; Not now leaves them alone."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Yes, join", callback_data=join_data),
        InlineKeyboardButton(text="Not now", callback_data="join_skip"),
    ]])
