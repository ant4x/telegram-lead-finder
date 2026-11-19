from html import escape

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from core.database.queries import add_niche, add_niche_word, delete_niche, get_niches
from core.keyboards.niche_kb import niches_for_deletion_keyboard
from core.states.niche_states import NicheStates
from core.text import INVALID_KEYWORD, valid_keyword
from core.utils.messages import send_lines

WORDS_HINT = ("👉 Send its words one at a time: what people write when they need it, like сайт*, SEO, Next.js. "
              "A * at the end matches every word that starts with it: сайт* finds сайт, сайта and сайтом.\n"
              "🛑 Send /cancel when you're done.")


async def add_niche_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("➡️ Let's add a niche: the topic of the leads you want, like Websites and SEO.\n\n"
                         "👉 Send its name.")
    await state.set_state(NicheStates.waiting_for_name)


async def process_niche_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not valid_keyword(name):
        await message.answer(INVALID_KEYWORD)
        return

    owner_id = message.from_user.id
    existing = next((niche for niche in await get_niches(owner_id) if niche.name == name), None)
    niche_id = existing.id if existing else await add_niche(owner_id, name)
    await state.update_data(niche_id=niche_id)
    await state.set_state(NicheStates.waiting_for_word)

    if existing:
        words = ", ".join(existing.words) or "no words yet"
        head = f"ℹ️ <b>{escape(name)}</b> is already on your list ({escape(words)}). New words go to it."
    else:
        head = f"✅ Added the niche <b>{escape(name)}</b>."
    await message.answer(f"{head}\n\n{WORDS_HINT}", parse_mode="HTML")


async def process_niche_word(message: Message, state: FSMContext):
    word = message.text.strip()
    if not valid_keyword(word):
        await message.answer(INVALID_KEYWORD)
        return

    niche_id = (await state.get_data())["niche_id"]
    status = await add_niche_word(niche_id, word)
    if status == 'gone':
        await state.clear()
        await message.answer("🛑 This niche was removed meanwhile. Add it again with /add_niche.")
        return
    shown = escape(word.lower())
    result = f"✅ Added <b>{shown}</b>." if status == 'added' else f"ℹ️ <b>{shown}</b> is already in this niche."
    await message.answer(f"{result}\n\nSend another one, or /cancel to finish.", parse_mode="HTML")


async def list_niches_command(message: Message):
    niches = await get_niches(message.from_user.id)
    if not niches:
        await message.answer("📭 No niches yet. Add one with /add_niche.")
        return

    lines = [f"▪️ <b>{escape(niche.name)}</b>: " + (escape(", ".join(niche.words)) or "<i>no words yet</i>")
             for niche in niches]
    await send_lines(message, "<b>🎯 Your niches:</b>", lines)


async def delete_niche_start(message: Message, state: FSMContext):
    await state.clear()
    niches = await get_niches(message.from_user.id)
    if not niches:
        await message.answer("🛑 No niches, nothing to remove.")
        return
    await message.answer("✍️ Tap a niche to remove it with its words:",
                         reply_markup=niches_for_deletion_keyboard(niches))


async def process_niche_deletion(callback: CallbackQuery):
    if callback.data == "del_niche_finish":
        await callback.message.edit_text("☑️ Done.")
        await callback.answer()
        return

    try:
        niche_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Something went wrong with that button.", show_alert=True)
        return

    owner_id = callback.from_user.id
    deleted = await delete_niche(niche_id, owner_id)
    niches = await get_niches(owner_id)
    if niches:
        await callback.message.edit_reply_markup(reply_markup=niches_for_deletion_keyboard(niches))
    else:
        await callback.message.edit_text("🛑 No niches left. Add one with /add_niche.")
    await callback.answer("✅ Removed" if deleted else "This niche isn't yours or is gone already.",
                          show_alert=not deleted)
