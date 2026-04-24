from aiogram.fsm.state import State, StatesGroup

class AdminEditState(StatesGroup):
    waiting_for_date = State()
    waiting_for_report_selection = State()
    waiting_for_report_action = State() # Просмотр: Редактировать / Удалить
    waiting_for_parameter_selection = State() # Выбор поля для правки
    
    # Состояния для конкретных полей (переиспользуем логику)
    waiting_for_new_value = State()
    
    # Состояния для удаления
    waiting_for_delete_confirm1 = State()
    waiting_for_delete_confirm2 = State()
