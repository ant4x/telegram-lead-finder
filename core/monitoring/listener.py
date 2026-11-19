import logging
from collections.abc import Awaitable, Callable
from html import escape
from telethon import events
from telethon.client import TelegramClient
from aiogram import Bot
from core.database.queries import (get_all_projects, find_channel_db_id_by_telegram_id,
                                      save_post, log_mention)
from core.text import mentions, post_link, quote

Handler = Callable[[events.NewMessage.Event], Awaitable[None]]


async def process_new_channel_post(event: events.NewMessage.Event, bot: Bot, admins: list[int]):
    """
    Records a new post that mentions a project and notifies the admins. Channels and projects are read
    from the database for every post, so the ones added or deleted by admins apply without a restart.
    """
    try:
        message_text = event.message.raw_text or ""
        if not message_text:
            return

        channel_db_id = await find_channel_db_id_by_telegram_id(event.chat_id)
        if not channel_db_id:
            return

        found = [(project_id, project_name) for project_id, project_name in await get_all_projects()
                 if mentions(message_text, project_name)]
        if not found:
            return

        chat = await event.get_chat()
        link = post_link(chat.username, chat.id, event.message.id)

        post_db_id = await save_post(
            channel_db_id=channel_db_id,
            message_id=event.message.id,
            link=link,
            post_date=event.message.date,
            text=message_text
        )
        for project_id, _ in found:
            await log_mention(post_db_id=post_db_id, project_db_id=project_id)

        projects_str = ", ".join(escape(project_name.capitalize()) for _, project_name in found)
        notification_text = (
            f"📢 <b>New mention</b>\n\n"
            f"<b>Project:</b> {projects_str}\n"
            f"<b>Channel:</b> {escape(chat.title)}\n\n"
            f"<i>“{quote(message_text)}”</i>\n\n"
            f"<a href='{link}'><b>Open the post</b></a>"
        )

        for admin_id in admins:
            try:
                await bot.send_message(admin_id, notification_text, parse_mode="HTML",
                                       disable_web_page_preview=True)
            except Exception as e:
                logging.error(f"Notification to admin {admin_id} failed: {e}")

    except Exception:
        logging.exception("New post handling failed")


async def dispatch(event: events.NewMessage.Event, handlers: list[Handler]):
    """Hands the message to every enabled module in turn; a module that fails does not stop the others."""
    for handle in handlers:
        try:
            await handle(event)
        except Exception:
            logging.exception("A module failed on a new message")


def start_monitoring(client: TelegramClient, handlers: list[Handler]):
    """Hands every new message of a channel or a group to the enabled modules while the client is connected."""

    @client.on(events.NewMessage(func=lambda event: event.is_channel))
    async def handler(event: events.NewMessage.Event):
        await dispatch(event, handlers)

    logging.info("Watching new posts")
