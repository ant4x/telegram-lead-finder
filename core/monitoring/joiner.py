"""
Joins watched channels with the reading account: Telegram sends new posts only to channel members.
Telegram publishes no limits for joining, so the account joins one channel at a time with a pause,
waits out a flood wait instead of retrying at once, and stops at the channel limit.
"""
import asyncio
import logging
from math import ceil

from aiogram import Bot
from telethon import TelegramClient
from telethon.errors import ChannelsTooMuchError, FloodWaitError
from telethon.tl.functions.channels import JoinChannelRequest

from core.database.queries import get_all_channels

JOIN_PAUSE_SECONDS = 60

# Channels waiting to be joined: the whole list at startup, then each channel added with /add_channel.
queue: asyncio.Queue = asyncio.Queue()


async def join_next(channel, pending: asyncio.Queue, join, notify, sleep=asyncio.sleep) -> bool:
    """Joins one channel and paces the next join. False when the account hit the channel limit and should stop."""
    try:
        joined = await join(channel)
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

    if joined:
        await sleep(JOIN_PAUSE_SECONDS)
    return True


async def run_joiner(bot: Bot, client: TelegramClient, admins: list[int]):
    """Joins every channel on the list, then each channel queued later, until the channel limit."""

    async def join(channel) -> bool:
        entity = await client.get_entity(channel)
        if not entity.left:
            logging.info(f"Already in {entity.title}")
            return False
        await client(JoinChannelRequest(entity))
        logging.info(f"Joined {entity.title}")
        return True

    async def notify(text: str):
        for admin_id in admins:
            try:
                await bot.send_message(admin_id, text)
            except Exception as e:
                logging.error(f"Message to admin {admin_id} failed: {e}")

    # Nobody awaits this task, so an error that stops it is logged here instead of vanishing.
    try:
        channels = await get_all_channels()
        logging.info(f"Checking {len(channels)} channels on the list to join")
        for channel in channels:
            queue.put_nowait(channel)
        while await join_next(await queue.get(), queue, join, notify):
            pass
    except Exception:
        logging.exception("Joining channels stopped")
