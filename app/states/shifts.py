from aiogram.fsm.state import State, StatesGroup

class ShiftState(StatesGroup):
    choosing_object = State()
    choosing_action = State()
    waiting_predecessor_confirm = State()
    choosing_planned_end = State()
