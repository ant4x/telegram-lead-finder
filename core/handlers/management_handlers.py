from html import escape

from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from core.keyboards.delete_kb import get_delete_choice_keyboard, get_delete_confirmation_keyboard
from core.utils.telethon_client import resolve_channel
from core.database.queries import add_channel, get_all_channels_with_details, delete_channel_by_id, \
    find_channel
from core.database.queries import (add_project, get_all_projects,
                                      delete_project_by_id)
from core.keyboards.project_management_kb import get_projects_for_deletion_keyboard
from core.keyboards.channel_management_kb import get_channels_for_deletion_keyboard
from core.states.management_states import AddChannelStates, DeleteChannelStates
from core.states.project_states import ProjectManagementStates
from core.utils.messages import send_lines
from core.monitoring.joiner import approve_awaiting, queue as join_queue
from core.keyboards.join_kb import join_keyboard
from core.text import INVALID_KEYWORD, plural, valid_keyword


async def add_channel_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("➡️ Let's add channels.\n\n"
                         "👉 Send a channel username, link or ID.\n"
                         "📡 Live alerts need the reading account to be in a channel. "
                         "I'll ask before it joins one.\n"
                         "🛑 Send /cancel when you're done.")
    await state.set_state(AddChannelStates.waiting_for_identifier)


async def process_channel_identifier(message: Message, state: FSMContext):
    channel_input = message.text.strip()

    try:
        channel_id, username, title, member = await resolve_channel(channel_input)
        status = await add_channel(channel_id=channel_id, username=username, title=title)

        result = f"✅ Added <b>{escape(title)}</b>." if status == 'added' else \
            f"ℹ️ <b>{escape(title)}</b> is already on the list."
        if member:
            await message.answer(f"{result}\n\nSend another one, or /cancel to finish.", parse_mode="HTML")
        else:
            await message.answer(f"{result}\n\n📡 The reading account isn't in it yet, and Telegram sends new posts "
                                 f"only to members. Join it with the account?\n\n"
                                 f"You can also send another channel, or /cancel to finish.",
                                 reply_markup=join_keyboard(f"join:{channel_id}"), parse_mode="HTML")

    except ValueError:
        await message.answer(f"❌ Couldn't find a channel for {channel_input}. Check it and try again, or send /cancel.")
    except Exception as e:
        await message.answer(f"🤷‍♂️ Something went wrong: {e}\n\nTry another channel, or send /cancel.")


async def cancel_dialog(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer("☑️ Canceled.")


async def list_channels_command(message: Message):
    channels = await get_all_channels_with_details()
    if not channels:
        await message.answer("❌ No channels yet. Add some with /add_channel.")
        return

    lines = [f"▪️ {escape(title)} (<code>{escape(identifier)}</code>)" for _, title, identifier in channels]
    lines.append(f"\n<b>🤙 Total: {len(channels)}</b>")
    await send_lines(message, "<b>📋 Watched channels:</b>", lines)


async def delete_channel_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "⁉️ How would you like to pick the channel to remove?",
        reply_markup=get_delete_choice_keyboard()
    )
    await state.set_state(DeleteChannelStates.waiting_for_choice)


async def process_delete_choice(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.split(":")[1]

    if choice == "from_list":
        channels = await get_all_channels_with_details()
        if not channels:
            await callback.message.edit_text("🌚 The list is empty, nothing to remove.")
            await state.clear()
        else:
            await callback.message.edit_text(
                "👉 Tap a channel to remove it:",
                reply_markup=get_channels_for_deletion_keyboard(channels)
            )
            await state.set_state(DeleteChannelStates.waiting_for_confirmation)
    elif choice == "by_name":
        await callback.message.edit_text("✍️ Send the username, link or ID of the channel to remove.")
        await state.set_state(DeleteChannelStates.waiting_for_name)
    elif choice == "cancel":
        await callback.message.edit_text("🛑 Canceled.")
        await state.clear()

    await callback.answer()


async def process_delete_from_list(callback: CallbackQuery, state: FSMContext):
    action = callback.data

    if action == "del_channel_finish":
        await callback.message.edit_text("🛑 Done.")
        await state.clear()
        await callback.answer()
        return

    try:
        channel_db_id = int(action.split(":")[1])
        await delete_channel_by_id(channel_db_id)
        await callback.answer("✅ Removed")

        new_channels_list = await get_all_channels_with_details()
        if not new_channels_list:
            await callback.message.edit_text("🛑 That was the last channel. The list is empty now.")
            await state.clear()
        else:
            await callback.message.edit_reply_markup(
                reply_markup=get_channels_for_deletion_keyboard(new_channels_list)
            )
    except (ValueError, IndexError):
        await callback.answer("❌ Something went wrong with that button.", show_alert=True)
        await callback.message.edit_text("❌ Something went wrong. Please try again.")
        await state.clear()


async def process_delete_by_name(message: Message, state: FSMContext):
    channel_input = message.text.strip()

    try:
        channel_id, _, telegram_title, _ = await resolve_channel(channel_input)
        result = await find_channel(channel_id)

        if not result:
            await message.answer(
                f"ℹ️ <b>{escape(telegram_title)}</b> isn't on your list. Try another channel, or send /cancel.",
                parse_mode="HTML")
            return

        db_id, title = result
        await message.answer(
            f"🧐 Remove <b>{escape(title)}</b> from the list?",
            reply_markup=get_delete_confirmation_keyboard(db_id),
            parse_mode="HTML"
        )
        await state.set_state(DeleteChannelStates.waiting_for_confirmation)

    except ValueError:
        await message.answer(f"❌ Couldn't find a channel for {channel_input}. Check it and try again, or send /cancel.")
    except Exception as e:
        await message.answer(f"🤷‍♂️ Something went wrong: {e}\n\nTry another channel, or send /cancel.")


async def process_delete_confirmation(callback: CallbackQuery, state: FSMContext):
    _, choice = callback.data.split(":")

    if choice == "cancel":
        await callback.message.edit_text("🛑 OK, keeping it.")
    else:
        await delete_channel_by_id(int(choice))
        await callback.message.edit_text("✅ Removed.")

    await callback.answer()
    await state.clear()


async def add_project_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("➡️ Let's add projects to watch.\n\n"
                         "👉 Send a project name. I match whole words and ignore case. "
                         "Add * at the end to match any word that starts with it: crypt* finds crypto and cryptocurrency.\n"
                         "🛑 Send /cancel when you're done.")
    await state.set_state(ProjectManagementStates.waiting_for_add_name)


async def process_project_add_name(message: Message, state: FSMContext):
    project_name = message.text.strip()

    if not valid_keyword(project_name):
        await message.answer(INVALID_KEYWORD)
        return

    status = await add_project(project_name)

    if status == 'added':
        await message.answer(f"✅ Added <b>{escape(project_name)}</b>.\n\n"
                             f"Send another one, or /cancel to finish.", parse_mode="HTML")
    elif status == 'exists':
        await message.answer(f"ℹ️ <b>{escape(project_name)}</b> is already on the list.\n\n"
                             f"Send another one, or /cancel to finish.", parse_mode="HTML")


async def list_projects_command(message: Message):
    projects = await get_all_projects()

    if not projects:
        await message.answer("🛑 No projects yet. Add the first one with /add_project.")
        return

    lines = [f"▪️ {escape(name.capitalize())}" for _, name in projects]
    lines.append(f"\n<b>Total: {len(projects)}</b>")
    await send_lines(message, "<b>Watched projects:</b>\n", lines)


async def delete_project_start(message: Message, state: FSMContext):
    await state.clear()
    projects = await get_all_projects()
    if not projects:
        await message.answer("🛑 The list is empty, nothing to remove.")
        return

    await message.answer(
        "✍️ Tap a project to stop watching it:",
        reply_markup=get_projects_for_deletion_keyboard(projects)
    )


async def process_project_deletion(callback: CallbackQuery):
    action = callback.data

    if action == "del_project_finish":
        await callback.message.edit_text("🚷 Done.")
        await callback.answer()
        return

    try:
        project_db_id = int(action.split(":")[1])
        await delete_project_by_id(project_db_id)
        await callback.answer("✅ Removed")

        new_projects_list = await get_all_projects()
        if not new_projects_list:
            await callback.message.edit_text("🛑 That was the last project. The list is empty now.")
        else:
            await callback.message.edit_reply_markup(
                reply_markup=get_projects_for_deletion_keyboard(new_projects_list)
            )
    except (ValueError, IndexError):
        await callback.answer("❌ Something went wrong with that button.", show_alert=True)
        await callback.message.edit_text("❌ Something went wrong. Please try again.")


async def process_join(callback: CallbackQuery):
    """An admin let the reading account join one channel, or every channel the startup message listed."""
    if callback.data == "join_all":
        count = approve_awaiting()
        answer = f"✅ Joining {plural(count, 'channel')}. I'll report each join." if count else \
            "ℹ️ Nothing left to join."
    else:
        join_queue.put_nowait(int(callback.data.split(":")[1]))
        answer = "✅ Joining it. I'll tell you when it's done."
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(answer)
    await callback.answer()


async def process_join_skip(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("OK, not joining. No live alerts will come from those channels "
                                  "until the reading account is in them. I'll ask again after a restart.")
    await callback.answer()
