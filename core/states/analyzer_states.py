from aiogram.fsm.state import State, StatesGroup


class AnalyzeStates(StatesGroup):
    waiting_for_project_name = State()
    waiting_for_days = State()
    waiting_for_confirmation = State()
