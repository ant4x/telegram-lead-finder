from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_channels_for_deletion_keyboard(channels: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for db_id, title, identifier in channels:
        builder.row(
            InlineKeyboardButton(
                text=f"❌ {title[:30]}...",
                callback_data=f"del_channel:{db_id}"
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="☑️ Закончить",
            callback_data="del_channel_finish"
        )
    )
    return builder.as_markup()
