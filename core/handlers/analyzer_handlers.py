import asyncio
import logging
import re
from html import escape
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from core.analyzer.history_scanner import start_full_scan
from core.utils.telethon_client import client as telethon_client
from core.states.analyzer_states import AnalyzeStates
from core.keyboards.confirmation_kb import button_analyze_confirm
from core.keyboards.days_selection_kb import button_days_selection
from core.database.shillometr import get_all_channels
from core.utils.messages import send_lines


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
    await message.answer("1️⃣ Хорошо, начинаем анализ. Какой проект будем искать?")
    await state.set_state(AnalyzeStates.waiting_for_project_name)


async def process_project_name(message: Message, state: FSMContext):
    await state.update_data(project_name=message.text)
    await message.answer("2️⃣ Отлично. Теперь выберите период для анализа:",
        reply_markup=button_days_selection)
    await state.set_state(AnalyzeStates.waiting_for_days)


async def process_days_selection(callback: CallbackQuery, state: FSMContext):
    days = int(re.findall(r'\d+', callback.data)[0])

    await state.update_data(days=days)
    user_data = await state.get_data()
    project_name = user_data.get('project_name')

    await callback.message.edit_text(
        f"3️⃣ Итак, подведем итог:\n\n"
        f"Ищем упоминания проекта: <b>{escape(project_name)}</b>\n"
        f"Период анализа: последние <b>{days}</b> дней\n\n"
        f"Всё верно?",
        reply_markup=button_analyze_confirm,
        parse_mode="HTML"
    )
    await state.set_state(AnalyzeStates.waiting_for_confirmation)
    await callback.answer()

async def process_confirmation(callback: CallbackQuery, state: FSMContext, bot: Bot):
    global scan_task
    await callback.message.edit_reply_markup(reply_markup=None)

    if callback.data == "analyze_cancel":
        await callback.message.edit_text("🚫 Анализ отменен.")
    else:
        user_data = await state.get_data()
        project_name = user_data.get('project_name')
        days = user_data.get('days')
        channels_from_db = await get_all_channels()

        if not channels_from_db:
            await callback.message.edit_text("🚫 В базе данных нет каналов для анализа. "
                                             "Сначала добавьте их с помощью команды /add_channel.")
        # No await between this check and create_task, so two presses cannot both start a scan.
        elif scan_task and not scan_task.done():
            await callback.message.edit_text("⚠️ В данный момент уже выполняется другой анализ. "
                                             "Пожалуйста, дождитесь его завершения и попробуйте снова.")
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
                f"✅ Отлично! Запускаю анализ проекта '<b>{escape(project_name)}</b>' за последние <b>{days}</b> дней.\n\n"
                f"Это может занять несколько минут. Результаты придут отдельным сообщением.",
                parse_mode="HTML"
            )

    await callback.answer()
    await state.clear()


REPORT_ANSWERS = {
    "report_channels": None,
    "report_posts": "✅ Ссылки отправлены!",
    "report_all": "✅ Полная информация отправлена!",
}


async def process_report_details(callback: CallbackQuery):
    user_id = callback.from_user.id
    action = callback.data

    user_results = SCAN_RESULTS_CACHE.get(user_id)

    if not user_results:
        await callback.message.edit_text(
            "🤷‍♂️ К сожалению, результаты этого сканирования уже недоступны. Запустите новый анализ.")
        await callback.answer()
        return

    if action == "report_close":
        await callback.message.edit_text(
            "Меню детализации закрыто.\n\n"
            "Чтобы начать новый анализ, используйте команду /analyze."
        )

        if user_id in SCAN_RESULTS_CACHE:
            del SCAN_RESULTS_CACHE[user_id]
        await callback.answer()
        return

    if action in ("report_channels", "report_all"):
        await send_lines(callback.message, "<b>📄 Каналы с упоминаниями:</b>", user_results['channels'])
    if action in ("report_posts", "report_all"):
        await send_lines(callback.message, "<b>📄 Ссылки на посты с упоминаниями:</b>", user_results['links'])
    await callback.answer(text=REPORT_ANSWERS[action])
