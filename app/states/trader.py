from aiogram.fsm.state import State, StatesGroup

class TraderScheduleState(StatesGroup):
    selecting_object = State()
    selecting_date = State()
    selecting_action = State()   # Выбор: Не працює или Интервалы
    selecting_start_hour = State()
    selecting_start_minute = State()
    selecting_end_hour = State()
    selecting_end_minute = State()
    selecting_power = State()
    selecting_mode = State()
    asking_next_interval = State()
    waiting_for_confirmation = State()

class TraderParserState(StatesGroup):
    reviewing = State()      # Просмотр распознанного (Подтвердить/Редактировать)
    selecting_obj = State()  # Выбор объекта для правки
    editing_obj = State()    # Меню правки конкретного объекта (Кнопки: Время, Мощность и т.д.)
    input_time = State()     # Ожидание ввода времени текстом
    confirm_revoke = State() # Ожидание подтверждения отзыва графика

