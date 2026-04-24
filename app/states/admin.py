from aiogram.fsm.state import State, StatesGroup

class AdminState(StatesGroup):
    waiting_for_role = State()
    waiting_for_user_phone = State()
    waiting_for_user_name = State()
    waiting_for_edit_name = State()
    waiting_for_edit_phone = State()
    
    # States for trader management
    waiting_for_trader_edit_name = State()
    waiting_for_trader_edit_phone = State()
    
    # States for object management
    waiting_for_object_name = State()
    waiting_for_edit_object_name = State()
    
class BroadcastState(StatesGroup):
    waiting_for_content = State() # Очікування тексту та/або фото
    confirming = State()         # Предпросмотр перед відправкою
    editing_existing = State()   # Редагування вже відправленого тексту
