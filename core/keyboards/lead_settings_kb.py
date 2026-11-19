from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from core.leads.preferences import KIND_NAMES, LeadSettings
from core.leads.rules import KINDS


def lead_settings_keyboard(settings: LeadSettings) -> InlineKeyboardMarkup:
    """One button per kind, marked when it is on."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"{'✅' if kind in settings.kinds else '▫️'} {KIND_NAMES[kind]}",
                             callback_data=f"lead_set:kind:{kind}")
        for kind in KINDS
    ]])
