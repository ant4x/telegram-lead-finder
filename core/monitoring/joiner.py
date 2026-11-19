"""
Joins watched channels with the reading account: Telegram sends new posts only to channel members.
The account joins only channels an admin has approved, one at a time with a pause, because Telegram
publishes no limits for joining; it waits out a flood wait instead of retrying at once and stops at the
channel limit. Admins hear about every join.
"""
import asyncio
import logging
from functools import partial
from math import ceil

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from telethon import TelegramClient
from telethon.errors import ChannelsTooMuchError, FloodWaitError, InviteRequestSentError
from telethon.tl.functions.channels import JoinChannelRequest

from core.database.queries import get_all_channels
from core.keyboards.join_kb import join_keyboard
from core.text import plural
from core.utils.entities import cached_entity

JOIN_PAUSE_SECONDS = 60
LISTED_TITLES = 30
NO_CHANNELS = "📭 No channels to watch yet. Add them with /add_channel."
BOT_CHECK = ("Groups often ask new members to prove they're not a bot within a minute. Open the reading account "
             "and pass the check, or the group may remove the account.")

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
    """
    Joins one channel or group and paces the next join. False when the account hit the channel limit and should stop.
    A chat that takes members by request gets one, and its admins decide.
    """
    try:
        joined = await join(channel)
    except FloodWaitError as e:
        await notify(f"⏳ Telegram asks to wait {ceil(e.seconds / 60)} min before joining more channels. "
                     f"I'll carry on after that.")
        await sleep(e.seconds)
        pending.put_nowait(channel)
        return True
    except InviteRequestSentError:
        await notify(f"📨 {channel} takes new members by request. The reading account sent one; live alerts start "
                     f"once the chat's admins approve it.")
        await sleep(JOIN_PAUSE_SECONDS)
        return True
    except ChannelsTooMuchError:
        await notify("⚠️ The reading account is in too many channels (Telegram allows about 500), so it stopped "
                     "joining new ones. Leave some channels and restart the bot to get live alerts from new ones.")
        return False
    except Exception as e:
        logging.exception(f"Joining {channel} failed")
        await notify(f"⚠️ Couldn't join {channel}: {e}. Check the chat, or remove it with /del_channel.")
        return True

    if joined:
        warning = f"\n\n⚠️ {BOT_CHECK}" if getattr(joined, "megagroup", False) else ""
        await notify(f"📡 The reading account joined {joined.title}, so live alerts from it can arrive.{warning}")
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
    """
    At startup: tells the admins the list is empty, or asks them about channels the account is not in.
    A chat that cannot be opened, deleted or turned private since it was added, is logged and skipped,
    and so is one that banned the account: Telegram returns it without the "left" field.
    """
    if not channels:
        await notify(NO_CHANNELS)
        return

    titles = []
    for channel in channels:
        try:
            entity = await get_entity(channel)
        except Exception as e:
            logging.warning(f"{channel} could not be opened: {e}")
            continue
        if not hasattr(entity, "left"):
            logging.warning(f"{channel} is not a chat the account can join; it may have banned the account")
            continue
        if entity.left:
            awaiting.append(channel)
            titles.append(entity.title)
    logging.info(f"The reading account is not in {plural(len(titles), 'channel')} on the list")
    if titles:
        await notify(approval_request(titles), join_keyboard("join_all"))


async def run_joiner(bot: Bot, client: TelegramClient, admins: list[int]):
    """Checks the channel list with the admins at startup, then joins the channels they approve."""

    async def join(channel):
        """The channel or group the account has just joined, or None when it is a member already."""
        entity = await cached_entity(client, channel)
        if not hasattr(entity, "left"):
            raise ValueError("it is not a chat the account can join; it may have banned the account")
        if not entity.left:
            logging.info(f"Already in {entity.title}")
            return None
        await client(JoinChannelRequest(entity))
        logging.info(f"Joined {entity.title}")
        return entity

    async def notify(text: str, keyboard: InlineKeyboardMarkup | None = None):
        for admin_id in admins:
            try:
                await bot.send_message(admin_id, text, reply_markup=keyboard)
            except Exception as e:
                logging.error(f"Message to admin {admin_id} failed: {e}")

    # Nobody awaits this task, so an error that stops it is logged here instead of vanishing.
    try:
        await check_channels(await get_all_channels(), partial(cached_entity, client), notify)
        while await join_next(await queue.get(), queue, join, notify):
            pass
    except Exception:
        logging.exception("Joining channels stopped")
