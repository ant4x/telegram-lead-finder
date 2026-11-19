import time
from html import escape

from aiogram import Bot
from aiogram.filters import CommandObject
from aiogram.types import CallbackQuery, Message

from core.analyzer.history_scanner import try_start_scan
from core.database.queries import (get_lead_settings, get_niches, lead_stats, save_lead_settings,
                                   set_lead_verdict)
from core.handlers.analyzer_handlers import ANOTHER_SEARCH
from core.keyboards.lead_kb import marked_keyboard
from core.keyboards.lead_settings_kb import lead_settings_keyboard
from core.leads.check import USAGE, parse_check_args, run_check
from core.leads.preferences import settings_text, toggle_kind
from core.leads.rules import KINDS
from core.leads.stats import STATS_SECONDS, stats_lines
from core.text import plural
from core.utils.messages import send_lines
from core.utils.telethon_client import client as telethon_client

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


async def check_chat_command(message: Message, command: CommandObject, bot: Bot):
    """Reads a chat's recent history for leads of the user's niches; one search runs at a time."""
    parsed = parse_check_args(command.args)
    if not parsed:
        await message.answer(USAGE)
        return

    chat, days = parsed
    user_id = message.from_user.id
    niches = await get_niches(user_id)
    if not niches:
        await message.answer("📭 Add a niche first with /add_niche: the check looks for its leads.")
        return
    if not try_start_scan(lambda: run_check(telethon_client, bot, user_id, chat, days, niches)):
        await message.answer(ANOTHER_SEARCH)
        return
    await message.answer(f"🔎 Checking {escape(chat)} for the last {plural(days, 'day')}. This can take a while.",
                         parse_mode="HTML")


async def lead_stats_command(message: Message):
    rows = await lead_stats(message.from_user.id, since=int(time.time()) - STATS_SECONDS)
    if not rows:
        await message.answer("📭 No leads in the last 30 days yet.")
        return
    await send_lines(message, "<b>📈 Leads in the last 30 days</b>", stats_lines(rows))
