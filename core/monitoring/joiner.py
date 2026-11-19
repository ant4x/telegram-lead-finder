"""
Joins watched channels with the reading account: Telegram sends new posts only to channel members.
The account joins only channels an admin has approved, one at a time with a pause, because Telegram
publishes no limits for joining; it waits out a flood wait instead of retrying at once and stops at the
channel limit. Admins hear about every join.
"""
import asyncio
import logging
from math import ceil

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from telethon import TelegramClient
from telethon.errors import ChannelsTooMuchError, FloodWaitError
from telethon.tl.functions.channels import JoinChannelRequest

from core.database.queries import get_all_channels
from core.keyboards.join_kb import join_keyboard
from core.text import plural

JOIN_PAUSE_SECONDS = 60
LISTED_TITLES = 30
NO_CHANNELS = "📭 No channels to watch yet. Add them with /add_channel."

# Channels an admin approved, in the order the account joins them.
queue: asyncio.Queue = asyncio.Queue()
# Channels on the list the account is not in, found at startup and waiting for an admin's answer.
awaiting: list = []


def approve_awaiting() -> int:
    """Moves every channel that waits for approval to the join queue; returns how many."""
    count = len(awaiting)
    for channel in awaiting:
        queue.put_nowait(channel)
    awaiting.clear()
    return count


async def join_next(channel, pending: asyncio.Queue, join, notify, sleep=asyncio.sleep) -> bool:
    """Joins one channel and paces the next join. False when the account hit the channel limit and should stop."""
    try:
        joined_title = await join(channel)
    except FloodWaitError as e:
        await notify(f"⏳ Telegram asks to wait {ceil(e.seconds / 60)} min before joining more channels. "
                     f"I'll carry on after that.")
        await sleep(e.seconds)
        pending.put_nowait(channel)
        return True
    except ChannelsTooMuchError:
        await notify("⚠️ The reading account is in too many channels (Telegram allows about 500), so it stopped "
                     "joining new ones. Leave some channels and restart the bot to get live alerts from new ones.")
        return False
    except Exception:
        logging.exception(f"Joining {channel} failed")
        return True

    if joined_title:
        await notify(f"📡 The reading account joined {joined_title}, so live alerts from it can arrive.")
        await sleep(JOIN_PAUSE_SECONDS)
    return True


def approval_request(titles: list[str]) -> str:
    """The question to the admins about channels on the list the account is not in."""
    them = "it" if len(titles) == 1 else "them"
    shown = "\n".join(f"▪️ {title}" for title in titles[:LISTED_TITLES])
    more = f"\n...and {len(titles) - LISTED_TITLES} more" if len(titles) > LISTED_TITLES else ""
    return (f"📡 The reading account isn't in {plural(len(titles), 'channel')} on the list, and Telegram sends new "
            f"posts only to members, so no live alerts come from {them}:\n{shown}{more}\n\n"
            f"Join {them}? The account joins one channel a minute, and each one shows up in its chat list.")


async def check_channels(channels: list, get_entity, notify):
    """At startup: tells the admins the list is empty, or asks them about channels the account is not in."""
    if not channels:
        await notify(NO_CHANNELS)
        return

    titles = []
    for channel in channels:
        entity = await get_entity(channel)
        if entity.left:
            awaiting.append(channel)
            titles.append(entity.title)
    logging.info(f"The reading account is not in {plural(len(titles), 'channel')} on the list")
    if titles:
        await notify(approval_request(titles), join_keyboard("join_all"))


async def run_joiner(bot: Bot, client: TelegramClient, admins: list[int]):
    """Checks the channel list with the admins at startup, then joins the channels they approve."""

    async def join(channel) -> str | None:
        """The title of the channel the account has just joined, or None when it is a member already."""
        entity = await client.get_entity(channel)
        if not entity.left:
            logging.info(f"Already in {entity.title}")
            return None
        await client(JoinChannelRequest(entity))
        logging.info(f"Joined {entity.title}")
        return entity.title

    async def notify(text: str, keyboard: InlineKeyboardMarkup | None = None):
        for admin_id in admins:
            try:
                await bot.send_message(admin_id, text, reply_markup=keyboard)
            except Exception as e:
                logging.error(f"Message to admin {admin_id} failed: {e}")

    # Nobody awaits this task, so an error that stops it is logged here instead of vanishing.
    try:
        await check_channels(await get_all_channels(), client.get_entity, notify)
        while await join_next(await queue.get(), queue, join, notify):
            pass
    except Exception:
        logging.exception("Joining channels stopped")
