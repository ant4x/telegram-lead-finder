from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

MARKS = {"reply": "✍️ You'll reply", "not_lead": "🚫 Marked: not a lead"}


def lead_keyboard(lead_id: int) -> InlineKeyboardMarkup:
    """The owner's answer to an alert, kept for the statistics."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✍️ I'll reply", callback_data=f"lead:reply:{lead_id}"),
        InlineKeyboardButton(text="🚫 Not a lead", callback_data=f"lead:not_lead:{lead_id}"),
    ]])


def marked_keyboard(verdict: str) -> InlineKeyboardMarkup:
    """Takes the place of the buttons once the owner has answered."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=MARKS[verdict], callback_data="lead:marked"),
    ]])
