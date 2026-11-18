from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def days_button(days: int) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=f"{days} days", callback_data=f"days_{days}")


def days_keyboard(admin: bool) -> InlineKeyboardMarkup:
    """7, 14 and 30 days for everyone; 90 and 180 days for admins only."""
    rows = [[days_button(7), days_button(14), days_button(30)]]
    if admin:
        rows.append([days_button(90), days_button(180)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
