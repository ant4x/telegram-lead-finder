import asyncio
import logging
from html import escape
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from core.analyzer.history_scanner import start_full_scan
from core.utils.telethon_client import client as telethon_client
from core.states.analyzer_states import AnalyzeStates
from core.keyboards.confirmation_kb import button_analyze_confirm
from core.keyboards.days_selection_kb import button_days_selection
from core.database.queries import get_all_channels
from core.utils.messages import send_lines
from core.text import INVALID_KEYWORD, valid_keyword


SCAN_RESULTS_CACHE = {}

# The running scan. Keeping the task here also keeps it alive: asyncio holds only a weak reference to tasks.
scan_task: asyncio.Task | None = None


async def run_scan(**kwargs):
    """One scan in the background. Nobody awaits the task, so its errors go to the log here."""
    try:
        await start_full_scan(**kwargs)
    except Exception:
        logging.exception("Scan failed")


async def start_dialog_analyzer(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("1️⃣ Which project should I look for? Add * at the end to match any word that starts with it.")
    await state.set_state(AnalyzeStates.waiting_for_project_name)


async def process_project_name(message: Message, state: FSMContext):
    project_name = message.text.strip()
    if not valid_keyword(project_name):
        await message.answer(INVALID_KEYWORD)
        return

    await state.update_data(project_name=project_name)
    await message.answer("2️⃣ How far back should I look?", reply_markup=button_days_selection)
    await state.set_state(AnalyzeStates.waiting_for_days)


async def process_days_selection(callback: CallbackQuery, state: FSMContext):
    days = int(callback.data.removeprefix('days_'))

    await state.update_data(days=days)
    user_data = await state.get_data()
    project_name = user_data.get('project_name')

    await callback.message.edit_text(
        f"3️⃣ Quick check:\n\n"
        f"Project: <b>{escape(project_name)}</b>\n"
        f"Period: last <b>{days}</b> days\n\n"
        f"Shall I start?",
        reply_markup=button_analyze_confirm,
        parse_mode="HTML"
    )
    await state.set_state(AnalyzeStates.waiting_for_confirmation)
    await callback.answer()


async def process_confirmation(callback: CallbackQuery, state: FSMContext, bot: Bot):
    global scan_task
    await callback.message.edit_reply_markup(reply_markup=None)

    if callback.data == "analyze_cancel":
        await callback.message.edit_text("🚫 Canceled.")
    else:
        user_data = await state.get_data()
        project_name = user_data.get('project_name')
        days = user_data.get('days')
        channels_from_db = await get_all_channels()

        if not channels_from_db:
            await callback.message.edit_text("🚫 There are no channels to search yet. "
                                             "Add some with /add_channel first.")
        # No await between this check and create_task, so two presses cannot both start a scan.
        elif scan_task and not scan_task.done():
            await callback.message.edit_text("⚠️ Another search is running. "
                                             "Please wait for it to finish and try again.")
        else:
            scan_task = asyncio.create_task(run_scan(
                client=telethon_client,
                bot=bot,
                user_id=callback.from_user.id,
                channels=channels_from_db,
                keywords=[project_name],
                results_cache=SCAN_RESULTS_CACHE,
                days=days
            ))
            await callback.message.edit_text(
                f"✅ Searching the last <b>{days}</b> days for <b>{escape(project_name)}</b>.\n\n"
                f"This can take a few minutes. I'll send the results in a new message.",
                parse_mode="HTML"
            )

    await callback.answer()
    await state.clear()


REPORT_ANSWERS = {
    "report_channels": None,
    "report_posts": "✅ Links sent",
    "report_all": "✅ Sent",
}


async def process_report_details(callback: CallbackQuery):
    user_id = callback.from_user.id
    action = callback.data

    user_results = SCAN_RESULTS_CACHE.get(user_id)

    if not user_results:
        await callback.message.edit_text(
            "🤷‍♂️ These results are no longer available. Run /analyze again.")
        await callback.answer()
        return

    if action == "report_close":
        await callback.message.edit_text(
            "Closed.\n\n"
            "Send /analyze to start a new search."
        )

        if user_id in SCAN_RESULTS_CACHE:
            del SCAN_RESULTS_CACHE[user_id]
        await callback.answer()
        return

    if action in ("report_channels", "report_all"):
        await send_lines(callback.message, "<b>📄 Channels with mentions:</b>", user_results['channels'])
    if action in ("report_posts", "report_all"):
        await send_lines(callback.message, "<b>🔗 Posts with mentions:</b>", user_results['links'])
    await callback.answer(text=REPORT_ANSWERS[action])
