import logging
from html import escape
from telethon import events
from telethon.client import TelegramClient
from aiogram import Bot
from core.database.shillometr import (get_all_channels, get_all_projects,
                                      find_channel_db_id_by_telegram_id,
                                      save_post, log_mention)
from core.settings import settings
from core.text import quote


async def process_new_channel_post(
        event: events.NewMessage.Event,
        bot: Bot,
        projects_to_watch: list,
        admins_to_notify: list
):
    try:
        if event.message.reply_to_msg_id or event.message.fwd_from:
            return

        message_text = event.message.text or ""
        if not message_text:
            return

        telegram_channel_id = event.chat_id
        channel_db_id = await find_channel_db_id_by_telegram_id(telegram_channel_id)
        if not channel_db_id:
            logging.warning(f"🕵️ Получено сообщение из канала с ID {telegram_channel_id}, но он не найден в нашей БД.")
            return

        if event.chat.username:
            link = f"https://t.me/{event.chat.username}/{event.message.id}"
        else:
            clean_id = str(event.chat.id).replace('-100', '')
            link = f"https://t.me/c/{clean_id}/{event.message.id}"

        found = [(project_id, project_name) for project_id, project_name in projects_to_watch
                 if project_name.lower() in message_text.lower()]
        if found:
            post_db_id = await save_post(
                channel_db_id=channel_db_id,
                message_id=event.message.id,
                link=link,
                post_date=event.message.date,
                text=event.message.text
            )
            for project_id, _ in found:
                await log_mention(post_db_id=post_db_id, project_db_id=project_id)
            found_projects = [escape(project_name.capitalize()) for _, project_name in found]

            channel_title = escape(event.chat.title)
            projects_str = ", ".join(found_projects)
            notification_text = (
                f"📢 <b>Найдено упоминание!</b>\n\n"
                f"<b>Проект(ы):</b> {projects_str}\n"
                f"<b>Канал:</b> {channel_title}\n\n"
                f"<i>«{quote(message_text)}»</i>\n\n"
                f"<a href='{link}'><b>Перейти к сообщению</b></a>"
            )

            for admin_id in admins_to_notify:
                try:
                    await bot.send_message(admin_id, notification_text, parse_mode="HTML",
                                           disable_web_page_preview=True)
                except Exception as e:
                    logging.error(f"🚫 Не удалось отправить уведомление админу {admin_id}: {e}")

    except Exception as e:
        logging.error(f"❌ Ошибка в process_new_channel_post: {e}")


async def start_monitoring(bot: Bot, client: TelegramClient):
    logging.info("Загружаю данные для мониторинга из БД...")

    channels_to_watch = await get_all_channels()
    projects_to_watch = await get_all_projects()
    admins_to_notify = settings.bots.admins_id

    if not channels_to_watch:
        logging.warning("❗️ В базе данных нет каналов для мониторинга. Listener не будет запущен.")
        return
    if not projects_to_watch:
        logging.warning("❗️ В базе данных нет проектов для мониторинга. Listener не будет запущен.")
        return

    logging.info(f"✅ Мониторинг запускается. Каналов: {len(channels_to_watch)}, Проектов: {len(projects_to_watch)}")

    @client.on(events.NewMessage(chats=channels_to_watch))
    async def handler(event: events.NewMessage.Event):
        await process_new_channel_post(event, bot, projects_to_watch, admins_to_notify)

    async with client:
        logging.info("✅ Telethon-клиент запущен и отслеживает каналы в реальном времени!")
        await client.run_until_disconnected()
