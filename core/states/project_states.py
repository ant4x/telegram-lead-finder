from aiogram.fsm.state import State, StatesGroup


class ProjectManagementStates(StatesGroup):
    waiting_for_add_name = State()
    waiting_for_delete_name = State()