import asyncio
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


IS_SCAN_RUNNING = False
SCAN_RESULTS_CACHE = {}


async def run_scan_with_lock(*args, **kwargs):
    global IS_SCAN_RUNNING
    if IS_SCAN_RUNNING:
        return

    IS_SCAN_RUNNING = True
    print(">>> [LOCK] Анализ запущен, блокировка установлена.")
    try:
        await start_full_scan(*args, **kwargs)
    except Exception as e:
        print(f"ОШИБКА в задаче сканирования: {e}")
    finally:
        IS_SCAN_RUNNING = False
        print(">>> [LOCK] Анализ завершен, блокировка снята.")


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
    await callback.message.edit_reply_markup(reply_markup=None)

    if IS_SCAN_RUNNING:
        await callback.message.edit_text("⚠️ В данный момент уже выполняется другой анализ. "
                                         "Пожалуйста, дождитесь его завершения и попробуйте снова.")
        await state.clear()
        await callback.answer()
        return

    if callback.data == "analyze_confirm":
        user_data = await state.get_data()
        project_name = user_data.get('project_name')
        days = user_data.get('days')

        channels_from_db = await get_all_channels()

        if not channels_from_db:
            await callback.message.edit_text("🚫 В базе данных нет каналов для анализа. "
                                             "Сначала добавьте их с помощью команды /add_channel.")
            await state.clear()
            await callback.answer()
            return

        await callback.message.edit_text(
            f"✅ Отлично! Запускаю анализ проекта '<b>{escape(project_name)}</b>' за последние <b>{days}</b> дней.\n\n"
            f"Это может занять несколько минут. Результаты придут отдельным сообщением.",
            parse_mode="HTML"
        )

        asyncio.create_task(run_scan_with_lock(
            client=telethon_client,
            bot=bot,
            user_id=callback.from_user.id,
            channels=channels_from_db,
            keywords=[project_name],
            results_cache=SCAN_RESULTS_CACHE,
            days=days
        ))

    elif callback.data == "analyze_cancel":
        await callback.message.edit_text("🚫 Анализ отменен.")

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
