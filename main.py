import asyncio
import logging
from pathlib import Path
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.enums import ChatType
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
from core.database.queries import create_tables, seed_initial_channels
from core.monitoring.listener import start_monitoring
from core.monitoring.joiner import run_joiner


# Channels added on the first run, while the channel list is empty: one username or link per line.
SEED_CHANNELS_FILE = Path("seed_channels.txt")

ADMIN_COMMANDS = ("analyze", "add_channel", "del_channel", "list_channels", "add_project", "del_project",
                  "list_projects")


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Show the commands"),
        BotCommand(command="/analyze", description="📊 Search past posts for a project (admin)"),
        BotCommand(command="/add_channel", description="➕ Add a channel (admin)"),
        BotCommand(command="/del_channel", description="➖ Remove a channel (admin)"),
        BotCommand(command="/list_channels", description="📋 List watched channels (admin)"),
        BotCommand(command="/add_project", description="🧐 Watch a project (admin)"),
        BotCommand(command="/del_project", description="😒 Stop watching a project (admin)"),
        BotCommand(command="/list_projects", description="📋 List watched projects (admin)")
    ]
    await bot.set_my_commands(commands)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s"
    )

    bot = Bot(settings.bots.bot_token)
    dp = Dispatcher()
    await set_commands(bot)

    await create_tables()

    # aiogram hands a message to the first handler whose filters match, so the order matters: commands come
    # first and work even in the middle of a dialog, then the dialog steps, then the fallbacks.
    # Admin rights are checked on every message and button press, because anyone can send a bot any button data.
    admin = F.from_user.id.in_(set(settings.bots.admins_id))

    dp.message.register(start, Command(commands="start"))
    dp.message.register(cancel_dialog, Command(commands="cancel"))
    dp.message.register(start_dialog_analyzer, Command(commands="analyze"), admin)
    dp.message.register(add_channel_start, Command(commands="add_channel"), admin)
    dp.message.register(delete_channel_start, Command(commands="del_channel"), admin)
    dp.message.register(list_channels_command, Command(commands="list_channels"), admin)
    dp.message.register(add_project_start, Command(commands="add_project"), admin)
    dp.message.register(delete_project_start, Command(commands="del_project"), admin)
    dp.message.register(list_projects_command, Command(commands="list_projects"), admin)
    dp.message.register(admins_only, Command(*ADMIN_COMMANDS))

    dp.message.register(process_channel_identifier, AddChannelStates.waiting_for_identifier, F.text, admin)
    dp.message.register(process_delete_by_name, DeleteChannelStates.waiting_for_name, F.text, admin)
    dp.message.register(process_project_add_name, ProjectManagementStates.waiting_for_add_name, F.text, admin)
    dp.message.register(process_project_name, AnalyzeStates.waiting_for_project_name, F.text, admin)

    dp.callback_query.register(process_delete_choice, DeleteChannelStates.waiting_for_choice,
                               F.data.startswith("del_choice:"), admin)
    dp.callback_query.register(process_delete_from_list, F.data.startswith("del_channel"), admin)
    dp.callback_query.register(process_delete_confirmation, F.data.startswith("del_confirm:"), admin)
    dp.callback_query.register(process_project_deletion, F.data.startswith("del_project"), admin)
    dp.callback_query.register(process_days_selection, AnalyzeStates.waiting_for_days,
                               F.data.startswith("days_"), admin)
    dp.callback_query.register(process_confirmation, AnalyzeStates.waiting_for_confirmation,
                               F.data.in_({"analyze_confirm", "analyze_cancel"}), admin)
    dp.callback_query.register(
        process_report_details,
        F.data.in_({"report_channels", "report_posts", "report_all", "report_close"}), admin
    )

    # Anything else in a private chat outside a dialog: text, unknown commands, photos, stickers.
    # In a group the bot stays silent instead of answering every message.
    dp.message.register(filter_text, StateFilter(None), F.chat.type == ChatType.PRIVATE)

    try:
        await telethon_client.start()
        logging.info("Telethon client started")

        await seed_initial_channels(resolve_channel, SEED_CHANNELS_FILE.read_text(encoding="utf-8").split())
        start_monitoring(bot, telethon_client)
        joiner = asyncio.create_task(run_joiner(bot, telethon_client, settings.bots.admins_id))  # the variable keeps the task alive

        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)

    finally:
        await telethon_client.disconnect()
        logging.info("Telethon client stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
