from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


button_days_selection = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="7 days", callback_data="days_7"),
            InlineKeyboardButton(text="14 days", callback_data="days_14"),
            InlineKeyboardButton(text="30 days", callback_data="days_30"),
        ],
        [
            InlineKeyboardButton(text="90 days", callback_data="days_90"),
            InlineKeyboardButton(text="180 days", callback_data="days_180"),
        ]
    ]
)