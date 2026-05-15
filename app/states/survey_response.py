from aiogram.fsm.state import State, StatesGroup

class SurveyResponseState(StatesGroup):
    waiting_for_photo = State()
    waiting_for_comment = State()
