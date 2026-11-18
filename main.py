import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import BotCommand
from aiogram.filters.state import StateFilter
from core.settings import settings
from core.handlers.basic import start, filter_text, admins_only
from core.handlers.management_handlers import (
    add_channel_start, process_channel_identifier, cancel_dialog, list_channels_command,
    delete_channel_start, process_delete_choice, process_delete_from_list,
    process_delete_by_name, process_delete_confirmation, add_project_start, process_project_add_name,
    list_projects_command, delete_project_start, process_project_deletion
)
from core.states.management_states import AddChannelStates, DeleteChannelStates
from core.states.project_states import ProjectManagementStates
from core.handlers.analyzer_handlers import (start_dialog_analyzer, process_project_name,
                                             process_days_selection, process_confirmation,
                                             process_report_details)
from core.states.analyzer_states import AnalyzeStates
from core.utils.telethon_client import client as telethon_client, resolve_channel
from core.database.shillometr import create_tables, seed_initial_channels
from core.monitoring.listener import start_monitoring


INITIAL_CHANNELS = []

ADMIN_COMMANDS = ("analyze", "add_channel", "del_channel", "list_channels", "add_project", "del_project",
                  "list_projects")


async def set_command(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Начать работу с ботом"),
        BotCommand(command="/analyze", description="📊 Анализ упоминаний проекта"),
        BotCommand(command="/add_channel", description="➕ [АДМИН] Добавить канал для мониторинга"),
        BotCommand(command="/del_channel", description="➖ [АДМИН] Удалить канал"),
        BotCommand(command="/list_channels", description="📋 [АДМИН] Список каналов"),
        BotCommand(command="/add_project", description="🧐 [АДМИН] Добавить проект в мониторинг"),
        BotCommand(command="/del_project", description="😒 [АДМИН] Удалить проект из мониторинга"),
        BotCommand(command="/list_projects", description="📋 [АДМИН] Список проектов для мониторинга")
    ]
    await bot.set_my_commands(commands)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s"
    )

    bot = Bot(settings.bots.bot_token)
    dp = Dispatcher()
    await set_command(bot)

    await create_tables()

    dp.message.register(start, Command(commands="start"))
    dp.message.register(cancel_dialog, Command(commands="cancel"))

    # Every other command, its dialog steps and its buttons are for admins only: the filter is checked on
    # each message and button press, because anyone can send a bot any button data.
    admin = F.from_user.id.in_(set(settings.bots.admins_id))

    dp.message.register(add_channel_start, Command(commands="add_channel"), admin)
    dp.message.register(process_channel_identifier, AddChannelStates.waiting_for_identifier, admin)

    dp.message.register(list_channels_command, Command(commands="list_channels"), admin)

    dp.message.register(delete_channel_start, Command(commands="del_channel"), admin)
    dp.callback_query.register(process_delete_choice, DeleteChannelStates.waiting_for_choice,
                               F.data.startswith("del_choice:"), admin)
    dp.message.register(process_delete_by_name, DeleteChannelStates.waiting_for_name, admin)
    dp.callback_query.register(process_delete_from_list, F.data.startswith("del_channel"), admin)
    dp.callback_query.register(process_delete_confirmation, F.data.startswith("del_confirm:"), admin)

    dp.message.register(add_project_start, Command(commands="add_project"), admin)
    dp.message.register(process_project_add_name, ProjectManagementStates.waiting_for_add_name, admin)

    dp.message.register(list_projects_command, Command(commands="list_projects"), admin)

    dp.message.register(delete_project_start, Command(commands="del_project"), admin)
    dp.callback_query.register(process_project_deletion, F.data.startswith("del_project"), admin)

    dp.message.register(start_dialog_analyzer, Command("analyze"), admin)
    dp.message.register(process_project_name, AnalyzeStates.waiting_for_project_name, admin)
    dp.callback_query.register(process_days_selection, AnalyzeStates.waiting_for_days,
                               F.data.startswith("days_"), admin)
    dp.callback_query.register(process_confirmation, AnalyzeStates.waiting_for_confirmation,
                               F.data.in_({"analyze_confirm", "analyze_cancel"}), admin)
    dp.callback_query.register(
        process_report_details,
        F.data.in_({"report_channels", "report_posts", "report_all", "report_close"}), admin
    )

    dp.message.register(admins_only, Command(*ADMIN_COMMANDS))

    # Фильтры
    dp.message.register(filter_text, StateFilter(None), F.text & ~F.text.startswith('/'))
    content_type_filters = [
        F.photo, F.document, F.video, F.audio, F.voice, F.sticker,
        F.animation, F.video_note, F.contact, F.location, F.venue, F.poll, F.dice
    ]
    for content_filter in content_type_filters:
        dp.message.register(filter_text, StateFilter(None), content_filter)

    try:
        logging.info("Запускаю Telethon клиент...")
        await telethon_client.start()
        logging.info("Telethon клиент запущен.")

        await seed_initial_channels(resolve_channel, INITIAL_CHANNELS)

        logging.info("Запускаю фоновый мониторинг...")
        start_monitoring(bot, telethon_client)

        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)

    finally:
        logging.info("Останавливаю Telethon клиент...")
        await telethon_client.disconnect()
        logging.info("Telethon клиент остановлен.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
