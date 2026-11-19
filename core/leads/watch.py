"""
The lead finder's part of the listener: checks each new message of a watched chat and alerts the owners of the
niches it matches. The rules run first, so most messages are dropped before the database or the network is used;
the AI, when an owner has it on, sees only what the rules let through.
"""
import asyncio
import logging
import time
from datetime import datetime, timezone

from aiogram import Bot
from telethon import events

from core.database.queries import (find_channel_db_id_by_telegram_id, get_lead_settings, get_niches,
                                   record_ai_verdict, save_lead, seen_recently)
from core.keyboards.lead_kb import lead_keyboard
from core.leads.ai import (AI_CHECKS_PER_DAY, AI_LIMIT_REACHED, AiConfig, AiVerdict, ai_line, check_lead,
                           dropped_by_ai)
from core.leads.alert import alert_text, author_of
from core.leads.rules import Niche, lead_kind, matching_niches, text_hash
from core.limits import DailyLimit
from core.text import post_link

DEDUP_SECONDS = 24 * 3600

# AI checks per niche owner and UTC day, in memory: a restart starts the count again.
ai_limit = DailyLimit(AI_CHECKS_PER_DAY)

# Telethon handles each new message in a task of its own, and copies of one text often arrive from several chats
# at once. The check for a repeat and the save run under this lock, so only the first copy is saved and alerted.
dedup_lock = asyncio.Lock()


async def _send(bot: Bot, owner_id: int, text: str, **kwargs):
    try:
        await bot.send_message(owner_id, text, **kwargs)
    except Exception as e:
        logging.error(f"Message to {owner_id} failed: {e}")


async def _ai_verdict(bot: Bot, ai: AiConfig, check, limit: DailyLimit, owner_id: int, day, text: str,
                      niches: list[Niche], kind: str) -> tuple[AiVerdict | None, bool]:
    """
    The AI's verdict and whether the check failed; no check once the owner's checks for the day are used up.
    A check is counted before the request, so leads arriving together cannot all pass the last free check.
    """
    if limit.left(owner_id, day) <= 0:
        return None, False
    limit.use(owner_id, day)
    if limit.left(owner_id, day) == 0:
        await _send(bot, owner_id, AI_LIMIT_REACHED)
    verdict = await check(ai, text, niches, kind)
    return verdict, verdict is None


async def process_lead_message(event: events.NewMessage.Event, bot: Bot, ai: AiConfig, check=check_lead,
                               limit: DailyLimit = ai_limit, now=time.time):
    """
    Alerts every owner whose niches the message matches and who wants this kind of lead, once a day for the same
    text sent around. With the AI on, labels add its note and the filter keeps out what it rejects.
    """
    text = event.message.raw_text or ""
    if not text or event.out:
        return
    kind = lead_kind(text)
    if kind is None:
        return
    niches = matching_niches(text, await get_niches())
    if not niches:
        return
    channel_db_id = await find_channel_db_id_by_telegram_id(event.chat_id)
    if not channel_db_id:
        return
    sender = await event.get_sender()
    if getattr(sender, "bot", False):
        return

    chat = await event.get_chat()
    link = post_link(chat.username, chat.id, event.message.id)
    author = author_of(sender, chat.title)
    fingerprint = text_hash(text)
    created_at = int(now())
    day = datetime.fromtimestamp(created_at, timezone.utc).date()

    owners: dict[int, list[Niche]] = {}
    for niche in niches:
        owners.setdefault(niche.owner_id, []).append(niche)

    for owner_id, owner_niches in owners.items():
        settings = await get_lead_settings(owner_id)
        if kind not in settings.kinds:
            continue
        async with dedup_lock:
            if await seen_recently(owner_id, fingerprint, created_at - DEDUP_SECONDS):
                continue
            lead_id = await save_lead(owner_id, channel_db_id, event.message.id, link, author.name, kind, text,
                                      fingerprint, created_at)

        mode = settings.ai_mode if ai.enabled else "off"
        verdict, failed = (None, False) if mode == "off" else \
            await _ai_verdict(bot, ai, check, limit, owner_id, day, text, owner_niches, kind)
        lead_kind_shown = verdict.kind if verdict and verdict.kind else kind
        dropped = dropped_by_ai(mode, verdict, settings.kinds)
        if verdict:
            await record_ai_verdict(lead_id, lead_kind_shown, verdict.author, verdict.summary,
                                    "ai_dropped" if dropped else None)
        if dropped:
            continue
        await _send(bot, owner_id, alert_text(lead_kind_shown, [niche.name for niche in owner_niches], chat.title,
                                              author, text, link, ai_line(verdict, failed)),
                    parse_mode="HTML", disable_web_page_preview=True, reply_markup=lead_keyboard(lead_id))
