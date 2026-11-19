from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.leads.rules import Niche


def niches_for_deletion_keyboard(niches: list[Niche]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for niche in niches:
        builder.row(InlineKeyboardButton(text=f"❌ {niche.name}", callback_data=f"del_niche:{niche.id}"))
    builder.row(InlineKeyboardButton(text="☑️ Done", callback_data="del_niche_finish"))
    return builder.as_markup()
