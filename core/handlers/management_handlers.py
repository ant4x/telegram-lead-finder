from html import escape

from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from core.keyboards.delete_kb import get_delete_choice_keyboard, get_delete_confirmation_keyboard
from core.utils.telethon_client import resolve_channel
from core.database.shillometr import add_channel, get_all_channels_with_details, delete_channel_by_id, \
    find_channel
from core.database.shillometr import (add_project, get_all_projects,
                                      delete_project_by_id)
from core.keyboards.project_management_kb import get_projects_for_deletion_keyboard
from core.keyboards.channel_management_kb import get_channels_for_deletion_keyboard
from core.states.management_states import AddChannelStates, DeleteChannelStates
from core.states.project_states import ProjectManagementStates
from core.utils.messages import send_lines


async def add_channel_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("➡️ Вы вошли в режим добавления каналов.\n\n"
                         "👉 Отправьте юзернейм, ID, или ссылку на канал."
                         "🛑 Для выхода из режима введите /cancel.")
    await state.set_state(AddChannelStates.waiting_for_identifier)


async def process_channel_identifier(message: Message, state: FSMContext):
    channel_input = message.text.strip()

    try:
        channel_id, username, title = await resolve_channel(channel_input)
        status = await add_channel(channel_id=channel_id, username=username, title=title)

        if status == 'added':
            await message.answer(f"✅ Канал '<b>{escape(title)}</b>' добавлен.\n\n"
                                 f"Отправьте следующий или введите /cancel.", parse_mode="HTML")
        elif status == 'exists':
            await message.answer(f"ℹ️ Канал '<b>{escape(title)}</b>' уже есть в списке.\n\n"
                                 f"Отправьте другой или введите /cancel.", parse_mode="HTML")

    except ValueError:
        await message.answer(f"❌ Не удалось найти канал `{channel_input}`. Попробуйте еще раз или введите /cancel.")
    except Exception as e:
        await message.answer(f"🤷‍♂️ Произошла ошибка: {e}\n\nПопробуйте другой канал или введите /cancel.")


async def cancel_dialog(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer("☑️ Действие отменено. Вы вышли из текущего режима.")


async def list_channels_command(message: Message):
    channels = await get_all_channels_with_details()
    if not channels:
        await message.answer("❌ Список отслеживаемых каналов пуст. Добавьте каналы с помощью команды /add_channel.")
        return

    lines = [f"▪️ {escape(title)} (<code>{escape(identifier)}</code>)" for _, title, identifier in channels]
    lines.append(f"\n<b>🤙 Всего каналов в базе: {len(channels)}</b>")
    await send_lines(message, "<b>📋 Список отслеживаемых каналов:</b>", lines)


async def delete_channel_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "⁉️ Как вы хотите удалить канал?",
        reply_markup=get_delete_choice_keyboard()
    )
    await state.set_state(DeleteChannelStates.waiting_for_choice)


async def process_delete_choice(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.split(":")[1]

    if choice == "from_list":
        channels = await get_all_channels_with_details()
        if not channels:
            await callback.message.edit_text("🌚 Список каналов пуст, удалять нечего.")
            await state.clear()
        else:
            await callback.message.edit_text(
                "👉 Выберите канал для удаления из списка:",
                reply_markup=get_channels_for_deletion_keyboard(channels)
            )
            await state.set_state(DeleteChannelStates.waiting_for_confirmation)
    elif choice == "by_name":
        await callback.message.edit_text("✍️ Хорошо, отправьте юзернейм, ID или ссылку на канал который нужно удалить.")
        await state.set_state(DeleteChannelStates.waiting_for_name)
    elif choice == "cancel":
        await callback.message.edit_text("🛑 Действие отменено.")
        await state.clear()

    await callback.answer()


async def process_delete_from_list(callback: CallbackQuery, state: FSMContext):
    action = callback.data

    if action == "del_channel_finish":
        await callback.message.edit_text("🛑 Вы вышли из режима удаления каналов.")
        await state.clear()
        await callback.answer()
        return

    try:
        channel_db_id = int(action.split(":")[1])
        await delete_channel_by_id(channel_db_id)
        await callback.answer("✅ Канал удален!")

        new_channels_list = await get_all_channels_with_details()
        if not new_channels_list:
            await callback.message.edit_text("🛑 Последний канал был удален. Список пуст.")
            await state.clear()
        else:
            await callback.message.edit_reply_markup(
                reply_markup=get_channels_for_deletion_keyboard(new_channels_list)
            )
    except (ValueError, IndexError):
        await callback.answer("❌ Произошла ошибка при обработке вашего выбора.", show_alert=True)
        await callback.message.edit_text("❌ Произошла ошибка. Пожалуйста, попробуйте снова.")
        await state.clear()


async def process_delete_by_name(message: Message, state: FSMContext):
    channel_input = message.text.strip()

    try:
        channel_id, _, telegram_title = await resolve_channel(channel_input)
        result = await find_channel(channel_id)

        if not result:
            await message.answer(
                f"ℹ️ Канал '<b>{escape(telegram_title)}</b>' найден в Telegram, но его нет в вашем списке мониторинга. Попробуйте еще раз или введите /cancel.",
                parse_mode="HTML")
            return

        db_id, title = result
        await message.answer(
            f"🧐 Найден канал '<b>{escape(title)}</b>'. Вы уверены, что хотите удалить его из мониторинга?",
            reply_markup=get_delete_confirmation_keyboard(db_id),
            parse_mode="HTML"
        )
        await state.set_state(DeleteChannelStates.waiting_for_confirmation)

    except ValueError:
        await message.answer(
            f"❌ Не удалось найти канал `{channel_input}` в Telegram. Попробуйте еще раз или введите /cancel.")
    except Exception as e:
        await message.answer(
            f"🤷‍♂️ Произошла непредвиденная ошибка: {e}\n\nПопробуйте другой канал или введите /cancel.")


async def process_delete_confirmation(callback: CallbackQuery, state: FSMContext):
    action, *data = callback.data.split(":")

    if data[0] == "cancel":
        await callback.message.edit_text("🛑 Удаление отменено.")
    else:
        channel_db_id = int(data[0])
        await delete_channel_by_id(channel_db_id)
        await callback.message.edit_text("✅ Канал успешно удален.")

    await callback.answer()
    await state.clear()


async def add_project_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("➡️ Вы вошли в режим добавления проектов для мониторинга.\n\n"
                         "👉 Введите название проекта.\n"
                         "🛑 Для выхода из режима введите /cancel.")
    await state.set_state(ProjectManagementStates.waiting_for_add_name)


async def process_project_add_name(message: Message, state: FSMContext):
    project_name = message.text.strip()

    if not (1 < len(project_name) < 100):
        await message.answer(
            "⚠️ Название проекта слишком короткое или длинное. Попробуйте еще раз или введите /cancel.")
        return

    status = await add_project(project_name)

    if status == 'added':
        await message.answer(f"✅ Проект '<b>{escape(project_name)}</b>' добавлен.\n\n"
                             f"Отправьте следующий или введите /cancel.", parse_mode="HTML")
    elif status == 'exists':
        await message.answer(f"ℹ️ Проект '<b>{escape(project_name)}</b>' уже есть в списке.\n\n"
                             f"Отправьте другой или введите /cancel.", parse_mode="HTML")


async def list_projects_command(message: Message):
    projects = await get_all_projects()

    if not projects:
        await message.answer("🛑 Список отслеживаемых проектов пуст. Добавьте первый с помощью /add_project.")
        return

    lines = [f"▪️ {escape(name.capitalize())}" for _, name in projects]
    lines.append(f"\n<b>Всего проектов: {len(projects)}</b>")
    await send_lines(message, "<b>Проекты для отслеживания:</b>\n", lines)


async def delete_project_start(message: Message):
    projects = await get_all_projects()
    if not projects:
        await message.answer("🛑 Список проектов пуст, удалять нечего.")
        return

    await message.answer(
        "✍️ Выберите проект для удаления:",
        reply_markup=get_projects_for_deletion_keyboard(projects)
    )


async def process_project_deletion(callback: CallbackQuery):
    action = callback.data

    if action == "del_project_finish":
        await callback.message.edit_text("🚷 Вы вышли из режима удаления проектов.")
        await callback.answer()
        return

    try:
        project_db_id = int(action.split(":")[1])
        await delete_project_by_id(project_db_id)
        await callback.answer("✅ Проект удален!")

        new_projects_list = await get_all_projects()
        if not new_projects_list:
            await callback.message.edit_text("🛑 Последний проект был удален. Список пуст.")
        else:
            await callback.message.edit_reply_markup(
                reply_markup=get_projects_for_deletion_keyboard(new_projects_list)
            )
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка! Попробуйте снова.", show_alert=True)
        await callback.message.edit_text("❌ Произошла ошибка.")
