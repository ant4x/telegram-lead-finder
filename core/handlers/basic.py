import logging
from html import escape

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message


async def start(message: Message, bot: Bot):
    first_name = message.from_user.first_name or "не указано"

    await message.answer(
        f"👋 <b>Привет, {escape(first_name)}!</b>\n\n"
        f"📡 <i>Шиллит весь Telegram? Мы знаем, кто, где и сколько.</i>\n\n"
        f"<b>📌 Доступные команды:</b>\n"
        f"▶️ <b>/start</b> — Показать это сообщение\n"
        f"📊 <b>/analyze</b> — Запустить анализ проекта\n\n"
        f"<i><b>-----КАНАЛЫ-----</b></i>\n"
        f"➕ <b>/add_channel</b> - [АДМИН] Добавить канал\n"
        f"➖ <b>/del_channel</b> -[АДМИН] Удалить канал\n"
        f"📋 <b>/list_channels</b> - [АДМИН] Список каналов\n\n"
        f"<i><b>-----МОНИТОРИНГ-----</b></i>\n"
        f"🧐 <b>/add_project</b> -[АДМИН] Добавить проект в мониторинг\n"
        f"😒 <b>/del_project</b> -[АДМИН] Удалить проект из мониторинга\n"
        f"📋 <b>/list_projects</b> -[АДМИН] Список проектов для мониторинга\n",
        parse_mode="HTML"
    )


async def admins_only(message: Message):
    await message.answer("❌ У вас нет прав для выполнения этой команды.")


async def filter_text(message: Message, state: FSMContext):
    logging.info(f"filter_text получил сообщение: {message.text}")
    current_state = await state.get_state()
    if current_state is not None:
        return
    await message.answer("⚠️ Данный бот работает только со встроенными командами")
