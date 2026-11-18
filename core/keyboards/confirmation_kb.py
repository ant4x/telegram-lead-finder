from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


button_analyze_confirm = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yes, start", callback_data="analyze_confirm")
        ],
        [
            InlineKeyboardButton(text="🚫 No, cancel", callback_data="analyze_cancel")
        ]
    ]
)
