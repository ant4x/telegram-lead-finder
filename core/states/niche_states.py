from aiogram.fsm.state import State, StatesGroup


class NicheStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_word = State()
