"""
The lead finder's part of the listener: checks each new message of a watched chat and alerts the owners of the
niches it matches. The rules run first, so most messages are dropped before the database or the network is used.
"""
import logging
import time

from aiogram import Bot
from telethon import events

from core.database.queries import (find_channel_db_id_by_telegram_id, get_lead_settings, get_niches, save_lead,
                                   seen_recently)
from core.keyboards.lead_kb import lead_keyboard
from core.leads.alert import alert_text, author_of
from core.leads.rules import lead_kind, matching_niches, text_hash
from core.text import post_link

DEDUP_SECONDS = 24 * 3600


async def process_lead_message(event: events.NewMessage.Event, bot: Bot, now=time.time):
    """
    Alerts every owner whose niches the message matches and who wants this kind of lead, once a day for the same
    text sent around.
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

    owners: dict[int, list[str]] = {}
    for niche in niches:
        owners.setdefault(niche.owner_id, []).append(niche.name)

    for owner_id, niche_names in owners.items():
        if kind not in (await get_lead_settings(owner_id)).kinds:
            continue
        if await seen_recently(owner_id, fingerprint, created_at - DEDUP_SECONDS):
            continue
        lead_id = await save_lead(owner_id, channel_db_id, event.message.id, link, author.name, kind, text,
                                  fingerprint, created_at)
        try:
            await bot.send_message(owner_id, alert_text(kind, niche_names, chat.title, author, text, link),
                                   parse_mode="HTML", disable_web_page_preview=True,
                                   reply_markup=lead_keyboard(lead_id))
        except Exception as e:
            logging.error(f"Lead alert to {owner_id} failed: {e}")
