from aiogram.fsm.state import State, StatesGroup

class ReminderCommentStates(StatesGroup):
    waiting_for_comment = State()
