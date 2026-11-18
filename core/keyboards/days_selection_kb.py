from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


button_days_selection = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="7 дней", callback_data="days_7"),
            InlineKeyboardButton(text="14 дней", callback_data="days_14"),
            InlineKeyboardButton(text="30 дней", callback_data="days_30"),
        ],
        [
            InlineKeyboardButton(text="90 дней", callback_data="days_90"),
            InlineKeyboardButton(text="180 дней", callback_data="days_180"),
        ]
    ]
)