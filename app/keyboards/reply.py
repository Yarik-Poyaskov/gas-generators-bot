from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

def get_main_menu_keyboard(is_admin: bool = False, role: str = 'user') -> ReplyKeyboardMarkup:
    """Returns a persistent keyboard for the main menu based on user role."""
    keyboard = []
    
    # Кнопка графиков ГПУ (для трейдеров и админов)
    if role == 'trader' or is_admin:
        keyboard.append([KeyboardButton(text="Графік роботи ГПУ")])
    
    # Кнопки для обычных пользователей и админов
    if role != 'trader':
        keyboard.append([KeyboardButton(text="👤 Керування змінами")])
        keyboard.append([KeyboardButton(text="Подати чек-лист")])
        keyboard.append([KeyboardButton(text="Статус ГПУ")])
        keyboard.append([KeyboardButton(text="📊Звіт показників роботи ГПУ за місяць(різниця показників газу)")])
        keyboard.append([KeyboardButton(text="📊Звіт показників роботи ГПУ за місяць(показники газового коректора)")])
        
    # Специфические кнопки админа
    if is_admin:
        keyboard.append([KeyboardButton(text="Адмін панель")])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
    )

def get_shift_actions_kb() -> ReplyKeyboardMarkup:
    """Returns a keyboard for shift actions."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨‍🔧 Ваша зміна почалась?")],
            [KeyboardButton(text="🏁 Ваша зміна закінчилась?")],
            [KeyboardButton(text="Відміна")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def get_admin_main_keyboard() -> ReplyKeyboardMarkup:
    """Returns a keyboard for the admin panel."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Додати користувача")],
            [KeyboardButton(text="Список користувачів")],
            [KeyboardButton(text="Список трейдерів")],
            [KeyboardButton(text="Керування об'єктами")],
            [KeyboardButton(text="📊 Звіти та підсумки")],
            [KeyboardButton(text="Розсилка"), KeyboardButton(text="Налаштування")],
            [KeyboardButton(text="Назад до головного меню")]
        ],
        resize_keyboard=True,
    )

def get_admin_reports_keyboard() -> ReplyKeyboardMarkup:
    """Returns a keyboard for the reports section in admin panel."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Перегляд та коригування Чек-Листів")],
            [KeyboardButton(text="Звіт по трейдеру (на сьогодні)")],
            [KeyboardButton(text="Звіт по трейдеру (на завтра)")],
            [KeyboardButton(text="Звіт по об'єктам (за сьогодні)")],
            [KeyboardButton(text="Назад до адмін-панелі")],
            [KeyboardButton(text="До головного меню")]
        ],
        resize_keyboard=True,
    )

def get_admin_trader_edit_keyboard() -> ReplyKeyboardMarkup:
    """Returns a keyboard for editing/deleting a specific trader."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Змінити ім'я")],
            [KeyboardButton(text="Змінити номер")],
            [KeyboardButton(text="Видалити трейдера")],
            [KeyboardButton(text="Назад до списку трейдерів")]
        ],
        resize_keyboard=True,
    )

def get_objects_mgmt_keyboard() -> ReplyKeyboardMarkup:
    """Returns a keyboard for object management."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Додати об'єкт")],
            [KeyboardButton(text="Список об'єктів")],
            [KeyboardButton(text="Назад до адмін-панелі")],
            [KeyboardButton(text="Назад до головного меню")]
        ],
        resize_keyboard=True,
    )

def get_admin_user_edit_keyboard() -> ReplyKeyboardMarkup:
    """Returns a keyboard for editing/deleting a specific user."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Змінити ім'я користувача")],
            [KeyboardButton(text="Змінити номер телефону")],
            [KeyboardButton(text="Керувати об'єктами користувача")],
            [KeyboardButton(text="Видалити користувача")],
            [KeyboardButton(text="Назад до списку користувачів")]
        ],
        resize_keyboard=True,
    )

def get_work_mode_short_kb(hide_not_working: bool = False) -> ReplyKeyboardMarkup:
    """Returns a keyboard for work modes in short reports, optionally filtering out 'Not Working' ones."""
    buttons = [
        [KeyboardButton(text="Острів"), KeyboardButton(text="Мережа")]
    ]
    if not hide_not_working:
        buttons.append([KeyboardButton(text="Не працює, готова до пуску")])
        buttons.append([KeyboardButton(text="ГПУ в аварії, не готова до пуску.")])
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def get_gpu_status_short_launch_kb() -> ReplyKeyboardMarkup:
    """Returns a keyboard for short report status when 'Launch Time' is selected (No 'Not Working')."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Стабільна"), KeyboardButton(text="З аваріями")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def get_gpu_status_short_stop_kb() -> ReplyKeyboardMarkup:
    """Returns a keyboard for short report status when 'Stop Time' is selected (No 'Stable')."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="З аваріями"), KeyboardButton(text="Не працює")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def get_is_gpu_working_kb() -> ReplyKeyboardMarkup:
    """Returns a keyboard for the initial question: Is GPU working now?"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ ГПУ зараз працює")],
            [KeyboardButton(text="⛔️ ГПУ зараз НЕ працює")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def get_work_mode_active_kb() -> ReplyKeyboardMarkup:
    """Returns a keyboard for work modes when GPU IS working."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Острів"), KeyboardButton(text="Мережа")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def get_work_mode_not_active_kb() -> ReplyKeyboardMarkup:
    """Returns a keyboard for work modes when GPU IS NOT working."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Не працює, готова до пуску")],
            [KeyboardButton(text="ГПУ в аварії, не готова до пуску.")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def get_gpu_status_active_kb() -> ReplyKeyboardMarkup:
    """Returns a keyboard for GPU status when it was initially marked as WORKING."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Стабільна"), KeyboardButton(text="З аваріями")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def get_gpu_status_not_active_kb() -> ReplyKeyboardMarkup:
    """Returns a keyboard for GPU status when it was initially marked as NOT WORKING."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="З аваріями"), KeyboardButton(text="Не працює")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def get_work_mode_kb() -> ReplyKeyboardMarkup:
    """Returns a reply keyboard for selecting the work mode (Legacy)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Острів"),
                KeyboardButton(text="Мережа"),
            ],
            [KeyboardButton(text="Не працює, готова до пуску")],
            [KeyboardButton(text="ГПУ в аварії, не готова до пуску.")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def get_gpu_status_kb() -> ReplyKeyboardMarkup:
    """Returns a reply keyboard for selecting the GPU status (Legacy)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Стабільна"),
                KeyboardButton(text="З аваріями"),
            ],
            [KeyboardButton(text="Не працює")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def get_simple_cancel_kb() -> ReplyKeyboardMarkup:
    """Returns a ReplyKeyboardMarkup with only a 'Відміна' button."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Відміна")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def get_user_list_manage_kb() -> ReplyKeyboardMarkup:
    """Returns a keyboard for the user list view with only navigation buttons."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Назад до адмін-панелі")],
            [KeyboardButton(text="Назад до головного меню")]
        ],
        resize_keyboard=True,
    )

def get_cancel_keyboard(current_keyboard: ReplyKeyboardMarkup | ReplyKeyboardRemove) -> ReplyKeyboardMarkup | ReplyKeyboardRemove:
    if isinstance(current_keyboard, ReplyKeyboardRemove):
        return current_keyboard

    cancel_button = [KeyboardButton(text="Відміна")]
    new_keyboard_rows = current_keyboard.keyboard + [cancel_button]

    return ReplyKeyboardMarkup(
        keyboard=new_keyboard_rows,
        resize_keyboard=current_keyboard.resize_keyboard,
        one_time_keyboard=current_keyboard.one_time_keyboard,
        is_persistent=current_keyboard.is_persistent
    )
