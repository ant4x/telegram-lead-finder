from aiogram.types import CallbackQuery, Message

from core.database.queries import get_lead_settings, save_lead_settings, set_lead_verdict
from core.keyboards.lead_kb import marked_keyboard
from core.keyboards.lead_settings_kb import lead_settings_keyboard
from core.leads.preferences import settings_text, toggle_kind
from core.leads.rules import KINDS

VERDICTS = ("reply", "not_lead")


async def process_lead_verdict(callback: CallbackQuery):
    """The owner answered an alert: the answer is saved and the buttons give way to a mark."""
    if callback.data == "lead:marked":
        await callback.answer("Already marked.")
        return

    try:
        _, verdict, lead_id = callback.data.split(":")
        lead_id = int(lead_id)
    except ValueError:
        await callback.answer("❌ Something went wrong with that button.", show_alert=True)
        return

    if verdict not in VERDICTS or not await set_lead_verdict(lead_id, callback.from_user.id, verdict):
        await callback.answer("This lead isn't yours or no longer exists.", show_alert=True)
        return
    await callback.message.edit_reply_markup(reply_markup=marked_keyboard(verdict))
    await callback.answer()


async def lead_settings_command(message: Message):
    settings = await get_lead_settings(message.from_user.id)
    await message.answer(settings_text(settings), reply_markup=lead_settings_keyboard(settings), parse_mode="HTML")


async def process_lead_setting(callback: CallbackQuery):
    """A tap on a kind turns it on or off and redraws the settings."""
    _, field, value = (callback.data.split(":") + ["", ""])[:3]
    if field != "kind" or value not in KINDS:
        await callback.answer("❌ Something went wrong with that button.", show_alert=True)
        return

    settings = toggle_kind(await get_lead_settings(callback.from_user.id), value)
    await save_lead_settings(callback.from_user.id, settings)
    await callback.message.edit_text(settings_text(settings), reply_markup=lead_settings_keyboard(settings),
                                     parse_mode="HTML")
    await callback.answer()
