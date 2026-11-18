from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


button_report_details = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📄 Каналы", callback_data="report_channels"),
            InlineKeyboardButton(text="🔗 Посты", callback_data="report_posts"),
        ],
        [
            InlineKeyboardButton(text="📂 Показать всё", callback_data="report_all"),
        ],
        [
            InlineKeyboardButton(text="☑️ Закрыть", callback_data="report_close"),
        ]
    ]
)