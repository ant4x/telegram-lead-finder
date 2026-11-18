from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


button_analyze_confirm = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, все верно", callback_data="analyze_confirm")
        ],
        [
            InlineKeyboardButton(text="🚫 Нет, отменить", callback_data="analyze_cancel")
        ]
    ]
)
