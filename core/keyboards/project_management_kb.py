from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_projects_for_deletion_keyboard(projects: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for db_id, name in projects:
        builder.row(
            InlineKeyboardButton(
                text=f"❌ {name.capitalize()}",
                callback_data=f"del_project:{db_id}"
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="☑️ Done",
            callback_data="del_project_finish"
        )
    )
    return builder.as_markup()
