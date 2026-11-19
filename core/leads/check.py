"""
/check_chat: reads a chat's recent history with the lead rules, without joining it and without the AI check,
to show whether the chat is worth adding: the account cannot be in more than about 500 chats and never leaves one.
"""
import logging
from datetime import datetime, timedelta, timezone
from html import escape

from aiogram import Bot
from telethon.client import TelegramClient

from core.analyzer.history_scanner import Match, ScanResult, scan_chat
from core.leads.preferences import KIND_NAMES
from core.leads.rules import KINDS, Niche, lead_kind, matching_niches
from core.text import plural

DEFAULT_DAYS = 7
MAX_CHECK_DAYS = 30
EXAMPLES = 5
USAGE = "Send /check_chat @chat, or /check_chat @chat 14 for 14 days (up to 30)."


def parse_check_args(args: str | None) -> tuple[str, int] | None:
    """The chat and the number of days, 7 unless given and 30 at most; None when the chat is missing or days are bad."""
    parts = (args or "").split()
    if not 1 <= len(parts) <= 2:
        return None
    if len(parts) == 1:
        return parts[0], DEFAULT_DAYS
    if not parts[1].isdigit() or int(parts[1]) < 1:
        return None
    return parts[0], min(int(parts[1]), MAX_CHECK_DAYS)


def lead_matcher(niches: list[Niche]) -> Match:
    """The kind of lead a message is for these niches, or None."""
    def match(text: str) -> str | None:
        kind = lead_kind(text)
        return kind if kind and matching_niches(text, niches) else None
    return match


def check_report(chat: str, days: int, result: ScanResult | None) -> str:
    shown = escape(chat)
    period = f"the last {plural(days, 'day')}"
    if result is None:
        return f"❌ Couldn't read {shown}: it is private, hidden from people outside it, or doesn't exist."
    if result.scanned_posts == 0:
        return f"📭 No messages in {shown} for {period}, or it hides its history from people outside it."

    counts = " · ".join(f"{KIND_NAMES[kind]}: {sum(label == kind for label, _ in result.found)}" for kind in KINDS)
    lines = [f"🔎 <b>{shown}</b>, {period}", f"Messages checked: {result.scanned_posts}", counts, ""]
    if result.found:
        lines.append("Examples:")
        lines += [f"▪️ {escape(link)}" for _, link in result.found[:EXAMPLES]]
    else:
        lines.append("No leads for your niches here.")
    return "\n".join(lines)


async def run_check(client: TelegramClient, bot: Bot, user_id: int, chat: str, days: int, niches: list[Niche]):
    """One check in the background. Nobody awaits the task, so its errors go to the log here."""
    try:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        result = await scan_chat(client, chat, lead_matcher(niches), start_date)
        await bot.send_message(user_id, check_report(chat, days, result), parse_mode="HTML",
                               disable_web_page_preview=True)
    except Exception:
        logging.exception("Chat check failed")
