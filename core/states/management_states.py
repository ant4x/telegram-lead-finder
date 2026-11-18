from aiogram.fsm.state import State, StatesGroup


class AddChannelStates(StatesGroup):
    waiting_for_identifier = State()


class DeleteChannelStates(StatesGroup):
    waiting_for_choice = State()
    waiting_for_name = State()
    waiting_for_confirmation = State()