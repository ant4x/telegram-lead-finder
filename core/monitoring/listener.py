import logging
from html import escape
from telethon import events
from telethon.client import TelegramClient
from aiogram import Bot
from core.database.shillometr import (get_all_projects, find_channel_db_id_by_telegram_id,
                                      save_post, log_mention)
from core.settings import settings
from core.text import mentions, post_link, quote


async def process_new_channel_post(event: events.NewMessage.Event, bot: Bot):
    """
    Records a new post that mentions a project and notifies the admins. Channels and projects are read
    from the database for every post, so the ones added or deleted by admins apply without a restart.
    """
    try:
        if event.message.reply_to_msg_id or event.message.fwd_from:
            return

        message_text = event.message.text or ""
        if not message_text:
            return

        channel_db_id = await find_channel_db_id_by_telegram_id(event.chat_id)
        if not channel_db_id:
            return

        found = [(project_id, project_name) for project_id, project_name in await get_all_projects()
                 if mentions(message_text, project_name)]
        if not found:
            return

        link = post_link(event.chat.username, event.chat.id, event.message.id)

        post_db_id = await save_post(
            channel_db_id=channel_db_id,
            message_id=event.message.id,
            link=link,
            post_date=event.message.date,
            text=event.message.text
        )
        for project_id, _ in found:
            await log_mention(post_db_id=post_db_id, project_db_id=project_id)

        projects_str = ", ".join(escape(project_name.capitalize()) for _, project_name in found)
        notification_text = (
            f"📢 <b>Найдено упоминание!</b>\n\n"
            f"<b>Проект(ы):</b> {projects_str}\n"
            f"<b>Канал:</b> {escape(event.chat.title)}\n\n"
            f"<i>«{quote(message_text)}»</i>\n\n"
            f"<a href='{link}'><b>Перейти к сообщению</b></a>"
        )

        for admin_id in settings.bots.admins_id:
            try:
                await bot.send_message(admin_id, notification_text, parse_mode="HTML",
                                       disable_web_page_preview=True)
            except Exception as e:
                logging.error(f"🚫 Не удалось отправить уведомление админу {admin_id}: {e}")

    except Exception as e:
        logging.error(f"❌ Ошибка в process_new_channel_post: {e}")


def start_monitoring(bot: Bot, client: TelegramClient):
    """Hands every new post of a channel or a group to process_new_channel_post while the client is connected."""

    @client.on(events.NewMessage(func=lambda event: event.is_channel))
    async def handler(event: events.NewMessage.Event):
        await process_new_channel_post(event, bot)

    logging.info("✅ Мониторинг новых постов запущен.")
