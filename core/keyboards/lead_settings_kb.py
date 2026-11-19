from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from core.leads.preferences import AI_MODE_NAMES, AI_MODES, KIND_NAMES, LeadSettings, mark
from core.leads.rules import KINDS


def lead_settings_keyboard(settings: LeadSettings, ai_available: bool) -> InlineKeyboardMarkup:
    """A button per kind, marked when it is on, and a row of AI modes when the AI check is set up."""
    rows = [[InlineKeyboardButton(text=f"{mark(kind in settings.kinds)} {KIND_NAMES[kind]}",
                                  callback_data=f"lead_set:kind:{kind}") for kind in KINDS]]
    if ai_available:
        rows.append([InlineKeyboardButton(text=f"{mark(mode == settings.ai_mode)} AI: {AI_MODE_NAMES[mode]}",
                                          callback_data=f"lead_set:ai:{mode}") for mode in AI_MODES])
    return InlineKeyboardMarkup(inline_keyboard=rows)
