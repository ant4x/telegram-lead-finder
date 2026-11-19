from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


button_report_details = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📄 Channels", callback_data="report_channels"),
            InlineKeyboardButton(text="🔗 Posts", callback_data="report_posts"),
        ],
        [
            InlineKeyboardButton(text="📂 Show all", callback_data="report_all"),
        ],
        [
            InlineKeyboardButton(text="☑️ Close", callback_data="report_close"),
        ]
    ]
)
