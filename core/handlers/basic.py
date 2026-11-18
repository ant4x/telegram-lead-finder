from html import escape

from aiogram.types import Message


async def start(message: Message):
    first_name = message.from_user.first_name or "there"

    await message.answer(
        f"👋 <b>Hi, {escape(first_name)}!</b>\n\n"
        f"📡 <i>Everyone shilling the same project? See who, where and how often.</i>\n\n"
        f"<b>📌 Commands</b>\n"
        f"▶️ <b>/start</b>: show this message\n"
        f"📊 <b>/analyze</b>: search past posts for a project (admin)\n"
        f"🛑 <b>/cancel</b>: stop the current step\n\n"
        f"<i><b>CHANNELS</b></i>\n"
        f"➕ <b>/add_channel</b>: add a channel (admin)\n"
        f"➖ <b>/del_channel</b>: remove a channel (admin)\n"
        f"📋 <b>/list_channels</b>: list watched channels (admin)\n\n"
        f"<i><b>LIVE ALERTS</b></i>\n"
        f"🧐 <b>/add_project</b>: watch a project (admin)\n"
        f"😒 <b>/del_project</b>: stop watching a project (admin)\n"
        f"📋 <b>/list_projects</b>: list watched projects (admin)\n",
        parse_mode="HTML"
    )


async def admins_only(message: Message):
    await message.answer("❌ Only admins can use this command.")


async def filter_text(message: Message):
    await message.answer("⚠️ I only understand commands. Send /start to see the list.")
