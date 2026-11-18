from html import escape

from aiogram.types import Message

from core.limits import SEARCHES_PER_DAY


async def start(message: Message):
    first_name = message.from_user.first_name or "there"

    await message.answer(
        f"👋 <b>Hi, {escape(first_name)}!</b>\n\n"
        f"📡 <i>Everyone shilling the same project? See who, where and how often.</i>\n\n"
        f"<b>📌 Commands</b>\n"
        f"▶️ <b>/start</b>: show this message\n"
        f"📊 <b>/analyze</b>: search past posts for a project ({SEARCHES_PER_DAY} a day)\n"
        f"🛑 <b>/cancel</b>: stop the current step\n\n"
        f"<i><b>FOR ADMINS</b></i>\n"
        f"➕ <b>/add_channel</b>: add a channel\n"
        f"➖ <b>/del_channel</b>: remove a channel\n"
        f"📋 <b>/list_channels</b>: list watched channels\n"
        f"🧐 <b>/add_project</b>: watch a project\n"
        f"😒 <b>/del_project</b>: stop watching a project\n"
        f"📋 <b>/list_projects</b>: list watched projects\n",
        parse_mode="HTML"
    )


async def admins_only(message: Message):
    await message.answer("❌ Only admins can use this command.")


async def filter_text(message: Message):
    await message.answer("⚠️ I only understand commands. Send /start to see the list.")
