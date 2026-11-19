import asyncio
import logging
from html import escape
from datetime import datetime, timedelta, timezone
from telethon.client import TelegramClient
from telethon.errors import FloodWaitError, ChannelPrivateError
from aiogram import Bot
from dataclasses import dataclass, field
from core.keyboards.report_details_kb import button_report_details
from core.text import mentions, plural, post_link

BATCH_DELAY_SECONDS = 3
CHANNEL_DELAY_SECONDS = 5


@dataclass
class ScanResult:
    scanned_posts: int = 0
    found_mentions: int = 0
    mention_links: list[str] = field(default_factory=list)


async def _scan_single_channel(client: TelegramClient, channel: str, keywords: list[str],
                               start_date: datetime) -> ScanResult | None:
    try:
        result = ScanResult()
        entity = await client.get_entity(channel)

        async for message in client.iter_messages(entity, limit=None):
            if message.date < start_date:
                break
            result.scanned_posts += 1

            if message.raw_text and any(mentions(message.raw_text, keyword) for keyword in keywords):
                result.found_mentions += 1
                result.mention_links.append(post_link(entity.username, entity.id, message.id))

            if result.scanned_posts % 100 == 0:
                await asyncio.sleep(BATCH_DELAY_SECONDS)

        logging.info(f"{channel}: {result.scanned_posts} posts in the period, {result.found_mentions} mentions")
        return result

    except (ValueError, ChannelPrivateError) as e:
        logging.warning(f"{channel} is not accessible: {e}")
        return None
    except FloodWaitError as e:
        # Telethon itself waits out limits of up to a minute (flood_sleep_threshold) and repeats the request,
        # so a wait that reaches this point is longer: the channel is skipped.
        logging.warning(f"{channel} skipped: Telegram asks to wait {e.seconds} seconds")
        return None
    except Exception:
        logging.exception(f"{channel} failed")
        return None


async def start_full_scan(
        client: TelegramClient,
        bot: Bot,
        user_id: int,
        channels: list[str],
        keywords: list[str],
        results_cache: dict,
        days: int = 7
):
    await bot.send_message(user_id,
                           f"▶️ Searching {plural(len(channels), 'channel')}. This can take a while.")

    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    total_posts_scanned = 0
    total_mentions_found = 0
    channels_with_mentions = set()
    all_mention_links = []
    successful_scans = 0
    failed_scans = 0

    for channel in channels:
        channel_result = await _scan_single_channel(client, channel, keywords, start_date)

        if channel_result:
            successful_scans += 1
            total_posts_scanned += channel_result.scanned_posts
            total_mentions_found += channel_result.found_mentions
            if channel_result.found_mentions > 0:
                channels_with_mentions.add(channel)
                all_mention_links.extend(channel_result.mention_links)
        else:
            failed_scans += 1

        await asyncio.sleep(CHANNEL_DELAY_SECONDS)

    mention_channels_count = len(channels_with_mentions)
    total_channels_count = len(channels)
    mention_percentage = (mention_channels_count / total_channels_count * 100) if total_channels_count > 0 else 0

    report_text = (
        f"🏁 <b>Done</b>\n\n"
        f"<b>Period:</b> last {days} days\n"
        f"<b>Searched for:</b> {escape(', '.join(keywords))}\n\n"
        f"<b><u>Summary</u></b>\n"
        f"▫️ Channels searched: {successful_scans} of {total_channels_count} (couldn't open: {failed_scans})\n"
        f"▫️ Posts checked: {total_posts_scanned}\n"
        f"▫️ <b>Mentions found: {total_mentions_found}</b>\n"
        f"▫️ Channels with mentions: <b>{mention_channels_count}</b> ({mention_percentage:.1f}%)"
    )

    await bot.send_message(user_id, report_text, parse_mode="HTML")

    if total_mentions_found > 0:
        sorted_channels = sorted([str(c) for c in channels_with_mentions])

        results_cache[user_id] = {
            'channels': sorted_channels,
            'links': all_mention_links
        }
        await bot.send_message(
            user_id,
            "Want the details?",
            reply_markup=button_report_details
        )
