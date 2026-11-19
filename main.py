import asyncio
import logging
from functools import partial
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.enums import ChatType
from aiogram.types import BotCommand
from aiogram.filters.state import StateFilter
from core.settings import settings
from core.access import can_use_leads
from core.commands import enabled_commands
from core.handlers.basic import start, filter_text, admins_only
from core.handlers.management_handlers import (
    add_channel_start, process_channel_identifier, cancel_dialog, list_channels_command,
    delete_channel_start, process_delete_choice, process_delete_from_list,
    process_delete_by_name, process_delete_confirmation, add_project_start, process_project_add_name,
    list_projects_command, delete_project_start, process_project_deletion, process_join, process_join_skip
)
from core.states.management_states import AddChannelStates, DeleteChannelStates
from core.states.project_states import ProjectManagementStates
from core.handlers.analyzer_handlers import (start_dialog_analyzer, process_project_name,
                                             process_days_selection, process_confirmation,
                                             process_report_details)
from core.states.analyzer_states import AnalyzeStates
from core.handlers.niche_handlers import (add_niche_start, process_niche_name, process_niche_word,
                                          list_niches_command, delete_niche_start, process_niche_deletion)
from core.states.niche_states import NicheStates
from core.handlers.lead_handlers import lead_settings_command, process_lead_setting, process_lead_verdict
from core.leads.watch import process_lead_message
from core.leads.retention import run_purge
from core.utils.telethon_client import client as telethon_client
from core.database.queries import create_tables
from core.monitoring.listener import process_new_channel_post, start_monitoring
from core.monitoring.joiner import run_joiner


async def set_commands(bot: Bot, modules: frozenset[str]):
    await bot.set_my_commands([
        BotCommand(command=f"/{command.name}",
                   description=f"{command.emoji} {command.description}" + (" (admin)" if command.admin else ""))
        for command in enabled_commands(modules)
    ])


def register_mentions_commands(dp: Dispatcher, admin):
    """The Shillometer: the history search for everyone, projects for admins."""
    dp.message.register(start_dialog_analyzer, Command(commands="analyze"))
    dp.message.register(add_project_start, Command(commands="add_project"), admin)
    dp.message.register(delete_project_start, Command(commands="del_project"), admin)
    dp.message.register(list_projects_command, Command(commands="list_projects"), admin)


def register_mentions_steps(dp: Dispatcher, admin):
    """The Shillometer's dialog steps and buttons."""
    dp.message.register(process_project_add_name, ProjectManagementStates.waiting_for_add_name, F.text, admin)
    dp.message.register(process_project_name, AnalyzeStates.waiting_for_project_name, F.text)

    dp.callback_query.register(process_project_deletion, F.data.startswith("del_project"), admin)
    dp.callback_query.register(process_days_selection, AnalyzeStates.waiting_for_days,
                               F.data.startswith("days_"))
    dp.callback_query.register(process_confirmation, AnalyzeStates.waiting_for_confirmation,
                               F.data.in_({"analyze_confirm", "analyze_cancel"}))
    dp.callback_query.register(
        process_report_details,
        F.data.in_({"report_channels", "report_posts", "report_all", "report_close"})
    )


def register_leads_commands(dp: Dispatcher, leads_user):
    """The lead finder's commands, for the users can_use_leads lets in."""
    dp.message.register(add_niche_start, Command(commands="add_niche"), leads_user)
    dp.message.register(list_niches_command, Command(commands="list_niches"), leads_user)
    dp.message.register(delete_niche_start, Command(commands="del_niche"), leads_user)
    dp.message.register(lead_settings_command, Command(commands="lead_settings"), leads_user)


def register_leads_steps(dp: Dispatcher, leads_user):
    """The lead finder's dialog steps and buttons."""
    dp.message.register(process_niche_name, NicheStates.waiting_for_name, F.text, leads_user)
    dp.message.register(process_niche_word, NicheStates.waiting_for_word, F.text, leads_user)

    dp.callback_query.register(process_niche_deletion, F.data.startswith("del_niche"), leads_user)
    dp.callback_query.register(process_lead_verdict, F.data.startswith("lead:"), leads_user)
    dp.callback_query.register(process_lead_setting, F.data.startswith("lead_set:"), leads_user)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s"
    )

    modules = settings.modules
    bot = Bot(settings.bots.bot_token)
    dp = Dispatcher()
    await set_commands(bot, modules)

    await create_tables()

    # aiogram hands a message to the first handler whose filters match, so the order matters: commands come
    # first and work even in the middle of a dialog, then the dialog steps, then the fallbacks.
    # The history search is for everyone, within the limits in core/limits.py. Everything else is for admins,
    # checked on every message and button press, because anyone can send a bot any button data.
    admin = F.from_user.id.in_(set(settings.bots.admins_id))
    leads_user = F.from_user.id.func(partial(can_use_leads, admins=frozenset(settings.bots.admins_id)))
    admin_commands = [command.name for command in enabled_commands(modules) if command.admin]

    dp.message.register(start, Command(commands="start"))
    dp.message.register(cancel_dialog, Command(commands="cancel"))
    dp.message.register(add_channel_start, Command(commands="add_channel"), admin)
    dp.message.register(delete_channel_start, Command(commands="del_channel"), admin)
    dp.message.register(list_channels_command, Command(commands="list_channels"), admin)
    if "mentions" in modules:
        register_mentions_commands(dp, admin)
    if "leads" in modules:
        register_leads_commands(dp, leads_user)
    dp.message.register(admins_only, Command(*admin_commands))

    dp.message.register(process_channel_identifier, AddChannelStates.waiting_for_identifier, F.text, admin)
    dp.message.register(process_delete_by_name, DeleteChannelStates.waiting_for_name, F.text, admin)

    dp.callback_query.register(process_delete_choice, DeleteChannelStates.waiting_for_choice,
                               F.data.startswith("del_choice:"), admin)
    dp.callback_query.register(process_delete_from_list, F.data.startswith("del_channel"), admin)
    dp.callback_query.register(process_delete_confirmation, F.data.startswith("del_confirm:"), admin)
    dp.callback_query.register(process_join, F.data.startswith("join:") | (F.data == "join_all"), admin)
    dp.callback_query.register(process_join_skip, F.data == "join_skip", admin)
    if "mentions" in modules:
        register_mentions_steps(dp, admin)
    if "leads" in modules:
        register_leads_steps(dp, leads_user)

    # Anything else in a private chat outside a dialog: text, unknown commands, photos, stickers.
    # In a group the bot stays silent instead of answering every message.
    dp.message.register(filter_text, StateFilter(None), F.chat.type == ChatType.PRIVATE)

    handlers = []
    if "mentions" in modules:
        handlers.append(partial(process_new_channel_post, bot=bot, admins=settings.bots.admins_id))
    if "leads" in modules:
        handlers.append(partial(process_lead_message, bot=bot))
        purge = asyncio.create_task(run_purge())  # the variable keeps the task alive

    try:
        await telethon_client.start()
        logging.info("Telethon client started")

        start_monitoring(telethon_client, handlers)
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
