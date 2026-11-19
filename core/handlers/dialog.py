from aiogram.fsm.context import FSMContext
from aiogram.types import Message


async def cancel_dialog(message: Message, state: FSMContext):
    """Ends the current step. /cancel is in the command menu, so outside a step it says so instead of staying silent."""
    if await state.get_state() is None:
        await message.answer("ℹ️ Nothing to cancel.")
        return

    await state.clear()
    await message.answer("☑️ Stopped. Anything you added stays.")
