from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_delete_choice_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⌨️ Type it in", callback_data="del_choice:by_name")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Pick from the list", callback_data="del_choice:from_list")
    )
    builder.row(
        InlineKeyboardButton(text="🚫 Cancel", callback_data="del_choice:cancel")
    )
    return builder.as_markup()


def get_delete_confirmation_keyboard(channel_db_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Yes, remove", callback_data=f"del_confirm:{channel_db_id}"),
        InlineKeyboardButton(text="❌ No", callback_data=f"del_confirm:cancel")
    )
    return builder.as_markup()