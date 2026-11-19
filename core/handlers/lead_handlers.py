from aiogram.types import CallbackQuery

from core.database.queries import set_lead_verdict
from core.keyboards.lead_kb import marked_keyboard

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
