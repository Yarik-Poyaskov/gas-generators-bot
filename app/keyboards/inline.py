import re
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_apparatus_check_kb() -> InlineKeyboardMarkup:
    """Returns an inline keyboard for the apparatus check."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Підтверджую", callback_data="apparatus_checked")
            ]
        ]
    )

def get_launch_planned_kb() -> InlineKeyboardMarkup:
    """Generates an inline keyboard to ask if launch is planned for 'Not Working' mode."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Так планується", callback_data="launch_planned_yes"),
                InlineKeyboardButton(text="❌ Ні не планується", callback_data="launch_planned_no")
            ],
            [InlineKeyboardButton(text="❌ Відміна", callback_data="cancel_checklist")]
        ]
    )

def get_planned_work_mode_kb() -> InlineKeyboardMarkup:
    """Generates an inline keyboard to select planned work mode (Island/Grid)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Острів", callback_data="planned_mode:Острів"),
                InlineKeyboardButton(text="Мережа", callback_data="planned_mode:Мережа")
            ],
            [InlineKeyboardButton(text="❌ Відміна", callback_data="cancel_checklist")]
        ]
    )

def get_time_type_kb() -> InlineKeyboardMarkup:
    """Generates an inline keyboard to select time type for shortened checklist."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Це час запуску", callback_data="time_type:2. Час запуску"),
                InlineKeyboardButton(text="Це час зупинки", callback_data="time_type:2. Час зупинки")
            ],
            [InlineKeyboardButton(text="❌ Відміна", callback_data="cancel_checklist")]
        ]
    )

def get_power_type_kb() -> InlineKeyboardMarkup:
    """Generates an inline keyboard to select power type."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Планова", callback_data="power_type:Планова"),   
                InlineKeyboardButton(text="Поточна", callback_data="power_type:Поточна")    
            ],
            [InlineKeyboardButton(text="⏩ Пропустити", callback_data="power_type:skip")],
            [InlineKeyboardButton(text="❌ Відміна", callback_data="cancel_checklist")]
        ]
    )

def get_planned_power_type_kb() -> InlineKeyboardMarkup:
    """Generates an inline keyboard with only 'Planned' power type (hides 'Current')."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Планова", callback_data="power_type:Планова")
            ],
            [InlineKeyboardButton(text="⏩ Пропустити", callback_data="power_type:skip")],
            [InlineKeyboardButton(text="❌ Відміна", callback_data="cancel_checklist")]
        ]
    )

def get_only_skip_power_kb() -> InlineKeyboardMarkup:
    """Generates an inline keyboard with only 'Skip' power type (hides 'Planned' and 'Current')."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏩ Пропустити", callback_data="power_type:skip")],
            [InlineKeyboardButton(text="❌ Відміна", callback_data="cancel_checklist")]
        ]
    )

def get_short_power_type_kb() -> InlineKeyboardMarkup:
    """Generates an inline keyboard to select power type for short reports (no 'Planned' button)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Поточна", callback_data="power_type:Поточна")    
            ],
            [InlineKeyboardButton(text="⏩ Пропустити", callback_data="power_type:skip")],
            [InlineKeyboardButton(text="❌ Відміна", callback_data="cancel_checklist")]
        ]
    )

def get_skip_after_pressure_kb() -> InlineKeyboardMarkup:
    """Generates an inline keyboard to skip point 7 if GPU is not running."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏩ Пропустити, якщо ГПУ не працює", callback_data="skip_pressure_after")],
            [InlineKeyboardButton(text="❌ Відміна", callback_data="cancel_checklist")]
        ]
    )

def get_traders_inline_keyboard(traders: list, page: int, per_page: int) -> InlineKeyboardMarkup:
    """Generates an inline keyboard for trader list with pagination."""
    start_idx = page * per_page
    end_idx = start_idx + per_page
    current_traders = traders[start_idx:end_idx]
    
    keyboard = []
    for trader in current_traders:
        status = "👤" if trader['user_id'] else "⏳"
        button_text = f"{status} {trader['full_name']} ({trader['phone_number']})"
        keyboard.append([InlineKeyboardButton(text=button_text, callback_data=f"manage_trader:{trader['id']}")])
    
    # Pagination
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"traders_page:{page-1}"))
    
    total_pages = (len(traders) + per_page - 1) // per_page
    if total_pages > 1:
        pagination_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="ignore"))
    
    if end_idx < len(traders):
        pagination_row.append(InlineKeyboardButton(text="➡️", callback_data=f"traders_page:{page+1}"))
    
    if pagination_row:
        keyboard.append(pagination_row)
        
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_role_selection_kb() -> InlineKeyboardMarkup:
    """Returns an inline keyboard to select user role."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Користувач", callback_data="role:user"),
                InlineKeyboardButton(text="Трейдер", callback_data="role:trader")
            ],
            [InlineKeyboardButton(text="Відміна", callback_data="cancel_checklist")]
        ]
    )

def get_hour_selection_kb(is_not_working: bool = False) -> InlineKeyboardMarkup:
    """Generates an inline keyboard for hour selection (00-23) with a Cancel button."""
    keyboard_rows = []
    for row_num in range(0, 24, 6): # 4 rows of 6 hours
        row = []
        for hour in range(row_num, min(row_num + 6, 24)):
            row.append(InlineKeyboardButton(text=f"{hour:02d}", callback_data=f"select_hour_{hour:02d}"))
        keyboard_rows.append(row)
    
    if is_not_working:
        keyboard_rows.append([InlineKeyboardButton(text="⏩ Пропустити", callback_data="skip_time")])
        
    keyboard_rows.append([InlineKeyboardButton(text="Відміна", callback_data="cancel_checklist")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)


def get_minute_selection_kb(selected_hour: int, is_not_working: bool = False) -> InlineKeyboardMarkup:
    """
    Generates an inline keyboard for minute selection (00-59 in 5-minute steps)
    with a Cancel button and a "Back to Hours" button.
    """
    keyboard_rows = []
    for row_num in range(0, 60, 20): # 3 rows of minutes
        row = []
        for minute in range(row_num, min(row_num + 20, 60), 5):
            row.append(InlineKeyboardButton(text=f"{minute:02d}", callback_data=f"select_minute_{selected_hour:02d}_{minute:02d}"))
        keyboard_rows.append(row)
    
    navigation_row = [
        InlineKeyboardButton(text="⬅️ Назад до годин", callback_data="back_to_hours")
    ]
    if is_not_working:
        navigation_row.append(InlineKeyboardButton(text="⏩ Пропустити", callback_data="skip_time"))
    
    keyboard_rows.append(navigation_row)
    keyboard_rows.append([InlineKeyboardButton(text="Відміна", callback_data="cancel_checklist")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)


def get_users_inline_keyboard(users: list, page: int, users_per_page: int) -> InlineKeyboardMarkup:
    """Generates an inline keyboard for user list with pagination."""
    start_idx = page * users_per_page
    end_idx = start_idx + users_per_page
    current_users = users[start_idx:end_idx]
    
    keyboard = []
    
    # User buttons
    for user in current_users:
        status = "✅" if user['user_id'] else "⏳"
        
        # Parse object names: extract parts in parentheses
        obj_names_raw = user.get('object_names')
        if obj_names_raw:
            names = obj_names_raw.split('|')
            short_names = []
            for name in names:
                match = re.search(r'\((.*?)\)', name)
                if match:
                    short_names.append(match.group(1))
                else:
                    short_names.append(name)
            objs_display = ", ".join(short_names)
        else:
            objs_display = "немає об'єктів"
            
        button_text = f"{status} {user['full_name']} ({objs_display})"
        keyboard.append([InlineKeyboardButton(text=button_text, callback_data=f"manage_user:{user['id']}")])
    
    # Pagination buttons
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"users_page:{page-1}"))
    
    total_pages = (len(users) + users_per_page - 1) // users_per_page
    if total_pages > 1:
        pagination_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="ignore"))
    
    if end_idx < len(users):
        pagination_row.append(InlineKeyboardButton(text="➡️", callback_data=f"users_page:{page+1}"))
    
    if pagination_row:
        keyboard.append(pagination_row)
        
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_objects_inline_keyboard(objects: list, page: int, per_page: int) -> InlineKeyboardMarkup:
    """Generates an inline keyboard for objects list with pagination."""
    start_idx = page * per_page
    end_idx = start_idx + per_page
    current_objects = objects[start_idx:end_idx]
    
    keyboard = []
    
    # Object buttons
    for obj in current_objects:
        group_mark = "💬 " if obj.get('telegram_group_id') else ""
        button_text = f"🏢 {group_mark}{obj['name']}"
        keyboard.append([InlineKeyboardButton(text=button_text, callback_data=f"manage_obj:{obj['id']}")])
    
    # Pagination buttons
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"objs_page:{page-1}"))
    
    total_pages = (len(objects) + per_page - 1) // per_page
    if total_pages > 1:
        pagination_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="ignore"))
    
    if end_idx < len(objects):
        pagination_row.append(InlineKeyboardButton(text="➡️", callback_data=f"objs_page:{page+1}"))
    
    if pagination_row:
        keyboard.append(pagination_row)
        
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_groups_selection_kb(groups: list, object_id: int) -> InlineKeyboardMarkup:
    """Generates an inline keyboard for selecting a group to link to an object."""
    keyboard = []
    for g in groups:
        keyboard.append([InlineKeyboardButton(text=f"💬 {g['title']}", callback_data=f"link_grp:{object_id}:{g['tg_id']}")])
    
    # Option to unlink
    keyboard.append([InlineKeyboardButton(text="❌ Відв'язати групу", callback_data=f"link_grp:{object_id}:none")])
    keyboard.append([InlineKeyboardButton(text="Скасувати", callback_data="close_admin_inline")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_user_objects_setup_kb(all_objects: list, user_objects: list, user_db_id: int, page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    """Generates an inline keyboard for linking objects to a user with pagination."""
    user_obj_ids = {obj['id'] for obj in user_objects}
    
    start_idx = page * per_page
    end_idx = start_idx + per_page
    current_objects = all_objects[start_idx:end_idx]
    
    keyboard = []
    
    for obj in current_objects:
        is_linked = obj['id'] in user_obj_ids
        mark = "✅ " if is_linked else ""
        keyboard.append([
            InlineKeyboardButton(
                text=f"{mark}{obj['name']}", 
                callback_data=f"toggle_uobj:{user_db_id}:{obj['id']}:{page}"
            )
        ])
    
    # Pagination buttons
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"uobj_page:{user_db_id}:{page-1}"))
    
    total_pages = (len(all_objects) + per_page - 1) // per_page
    if total_pages > 1:
        pagination_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="ignore"))
    
    if end_idx < len(all_objects):
        pagination_row.append(InlineKeyboardButton(text="➡️", callback_data=f"uobj_page:{user_db_id}:{page+1}"))
        
    if pagination_row:
        keyboard.append(pagination_row)
    
    keyboard.append([InlineKeyboardButton(text="📥 Зберегти та вийти", callback_data="close_admin_inline")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_object_selection_kb(objects: list, page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    """Generates an inline keyboard for selecting an object during report start with pagination."""
    start_idx = page * per_page
    end_idx = start_idx + per_page
    current_objects = objects[start_idx:end_idx]
    
    keyboard = []
    for obj in current_objects:
        keyboard.append([InlineKeyboardButton(text=obj['name'], callback_data=f"select_obj:{obj['id']}")])
    
    # Pagination buttons
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"sel_obj_page:{page-1}"))
    
    total_pages = (len(objects) + per_page - 1) // per_page
    if total_pages > 1:
        pagination_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="ignore"))
    
    if end_idx < len(objects):
        pagination_row.append(InlineKeyboardButton(text="➡️", callback_data=f"sel_obj_page:{page+1}"))
        
    if pagination_row:
        keyboard.append(pagination_row)
    
    keyboard.append([InlineKeyboardButton(text="Відміна", callback_data="cancel_checklist")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_object_manage_kb(object_id: int) -> InlineKeyboardMarkup:
    """Generates an inline keyboard for managing a single object."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Змінити назву", callback_data=f"edit_obj_name:{object_id}")],
            [InlineKeyboardButton(text="💬 Прив'язати групу", callback_data=f"link_obj_grp:{object_id}")],
            [InlineKeyboardButton(text="👥 Показати користувачів", callback_data=f"show_obj_users:{object_id}")],
            [InlineKeyboardButton(text="🗑 Видалити об'єкт", callback_data=f"delete_obj:{object_id}")],
            [InlineKeyboardButton(text="⬅️ Назад до списку", callback_data="objs_page:0")]
        ]
    )

def get_report_confirm_kb() -> InlineKeyboardMarkup:
    """Returns an inline keyboard for final report confirmation."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Підтвердити", callback_data="confirm_report"),
                InlineKeyboardButton(text="❌ Відміна", callback_data="cancel_checklist")
            ]
        ]
    )


def get_trader_date_kb() -> InlineKeyboardMarkup:
    """Generates an inline keyboard for date selection for traders."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="На сьогодні", callback_data="trader_date:today"),
                InlineKeyboardButton(text="На завтра", callback_data="trader_date:tomorrow"),
                InlineKeyboardButton(text="На післязавтра", callback_data="trader_date:after_tomorrow")
            ],
            [InlineKeyboardButton(text="Відміна", callback_data="cancel_checklist")]
        ]
    )

def get_trader_action_kb() -> InlineKeyboardMarkup:
    """Generates an inline keyboard for choosing between 'Not working' and 'Intervals'."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Встановити 'не працює'", callback_data="trader_action:not_working")],
            [InlineKeyboardButton(text="⏱ Ввести інтервали роботи", callback_data="trader_action:intervals")],
            [InlineKeyboardButton(text="Відміна", callback_data="cancel_checklist")]
        ]
    )

def get_trader_hour_kb(label: str, prefix: str) -> InlineKeyboardMarkup:
    """Generates an inline keyboard for hour selection (00-23) for traders."""
    keyboard_rows = []
    for row_num in range(0, 24, 6): # 4 rows of 6 hours
        row = []
        for hour in range(row_num, min(row_num + 6, 24)):
            row.append(InlineKeyboardButton(text=f"{hour:02d}", callback_data=f"{prefix}:{hour:02d}"))
        keyboard_rows.append(row)
    
    keyboard_rows.append([InlineKeyboardButton(text="Відміна", callback_data="cancel_checklist")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

def get_trader_minute_kb(hour: int, prefix: str) -> InlineKeyboardMarkup:
    """
    Generates an inline keyboard for minute selection (00-59 in 5-minute steps)
    for trader intervals.
    """
    keyboard_rows = []
    for row_num in range(0, 60, 20): # 3 rows of minutes
        row = []
        for minute in range(row_num, min(row_num + 20, 60), 5):
            row.append(InlineKeyboardButton(text=f"{minute:02d}", callback_data=f"{prefix}:{hour:02d}:{minute:02d}"))
        keyboard_rows.append(row)
    
    keyboard_rows.append([InlineKeyboardButton(text="Відміна", callback_data="cancel_checklist")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

def get_power_percent_kb() -> InlineKeyboardMarkup:
    """Generates an inline keyboard for power percentage selection (0-100% in 10% steps)."""
    keyboard_rows = []
    for row_num in range(0, 110, 30):
        row = []
        for val in range(row_num, min(row_num + 30, 110), 10):
            row.append(InlineKeyboardButton(text=f"{val}%", callback_data=f"trader_power:{val}"))
        if row:
            keyboard_rows.append(row)
    
    keyboard_rows.append([InlineKeyboardButton(text="⏩ Пропустити", callback_data="trader_power:skip")])
    keyboard_rows.append([InlineKeyboardButton(text="Відміна", callback_data="cancel_checklist")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

def get_work_mode_trader_kb() -> InlineKeyboardMarkup:
    """Generates an inline keyboard for work mode selection for traders."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Мережа", callback_data="trader_mode:Мережа"),
                InlineKeyboardButton(text="Острів", callback_data="trader_mode:Острів")
            ],
            [InlineKeyboardButton(text="⏩ Пропустити", callback_data="trader_mode:skip")],
            [InlineKeyboardButton(text="Відміна", callback_data="cancel_checklist")]
        ]
    )

def get_next_interval_kb() -> InlineKeyboardMarkup:
    """Generates an inline keyboard to ask if trader wants to add another interval."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Додати ще інтервал", callback_data="trader_next:add"),
                InlineKeyboardButton(text="🏁 Завершити", callback_data="trader_next:finish")
            ],
            [InlineKeyboardButton(text="Відміна", callback_data="cancel_checklist")]
        ]
    )

def get_schedule_confirm_kb(schedule_id: int) -> InlineKeyboardMarkup:
    """Generates an inline keyboard for users to confirm a trader schedule."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Підтвердити графік", callback_data=f"confirm_sched:{schedule_id}")
            ]
        ]
    )

def get_confirmation_kb(confirm_data: str, cancel_data: str) -> InlineKeyboardMarkup:
    """Generates an inline keyboard for confirmation."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Так, впевнений", callback_data=confirm_data),
                InlineKeyboardButton(text="❌ Скасувати", callback_data=cancel_data)
            ]
        ]
    )

def get_edit_report_date_kb() -> InlineKeyboardMarkup:
    """Generates an inline keyboard for date selection in admin edit mode."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Сьогодні", callback_data="edit_date:today"),
                InlineKeyboardButton(text="Вчора", callback_data="edit_date:yesterday")
            ],
            [InlineKeyboardButton(text="Обрати іншу дату", callback_data="edit_date:calendar")],
            [InlineKeyboardButton(text="Відміна", callback_data="cancel_edit")]
        ]
    )

from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

KYIV_TZ = ZoneInfo("Europe/Kiev")

def get_report_list_kb(reports: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Generates an inline keyboard for reports list with pagination."""
    keyboard = []
    for r in reports:
        try:
            # created_at is stored as UTC string "YYYY-MM-DD HH:MM:SS"
            dt_utc = datetime.strptime(r['created_at'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            local_time = dt_utc.astimezone(KYIV_TZ)
            time_str = local_time.strftime("%H:%M")
        except:
            time_str = "??:??"
        
        obj_name = r['tc_name']
        match = re.search(r'\((.*?)\)', obj_name)
        display_name = match.group(1) if match else obj_name
        
        button_text = f"{time_str} | {display_name}"
        keyboard.append([InlineKeyboardButton(text=button_text, callback_data=f"edit_report:{r['id']}")])
    
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"edit_reports_page:{page-1}"))
    
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="ignore"))
        
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"edit_reports_page:{page+1}"))
        
    if nav_row:
        keyboard.append(nav_row)
        
    keyboard.append([InlineKeyboardButton(text="Назад к выбору даты", callback_data="back_to_edit_date")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_report_actions_kb(report_id: int) -> InlineKeyboardMarkup:
    """Actions for a specific report."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редагувати", callback_data=f"edit_fields:{report_id}")],
            [InlineKeyboardButton(text="🗑 Видалити звіт", callback_data=f"delete_report:{report_id}")],
            [InlineKeyboardButton(text="⬅️ Назад до списку", callback_data="back_to_report_list")]
        ]
    )

def get_report_fields_kb(report: dict) -> InlineKeyboardMarkup:
    """Menu of editable fields with current values."""
    fields = [
        ('work_mode', 'Режим роботи'),
        ('start_time', 'Час запуску'),
        ('gpu_status', 'Статус ГПУ'),
        ('battery_voltage', 'Напруга АКБ'),
        ('pressure_before', 'Тиск До'),
        ('pressure_after', 'Тиск Після'),
        ('total_mwh', 'Виробітка (МВт)'),
        ('total_hours', 'Мотогодини'),
        ('oil_sampling_limit', 'Ліміт мастила')
    ]
    
    keyboard = []
    for field_id, field_name in fields:
        val = report.get(field_id, '---')
        keyboard.append([InlineKeyboardButton(text=f"{field_name}: {val}", callback_data=f"edit_field:{field_id}")])
        
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_to_report_view:{report['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_edit_work_mode_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Острів", callback_data="set_val:work_mode:Острів")],
            [InlineKeyboardButton(text="Мережа", callback_data="set_val:work_mode:Мережа")],
            [InlineKeyboardButton(text="Не працює", callback_data="set_val:work_mode:Не працює")],
            [InlineKeyboardButton(text="⬅️ Скасувати", callback_data="back_to_fields")]
        ]
    )

def get_edit_gpu_status_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Стабільна", callback_data="set_val:gpu_status:Стабільна")],
            [InlineKeyboardButton(text="З аваріями", callback_data="set_val:gpu_status:З аваріями")],
            [InlineKeyboardButton(text="Не працює", callback_data="set_val:gpu_status:Не працює")],
            [InlineKeyboardButton(text="⬅️ Скасувати", callback_data="back_to_fields")]
        ]
    )

def get_short_stop_power_kb() -> InlineKeyboardMarkup:
    """Returns a keyboard for short report STOP time (only Skip/Cancel)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏩ Пропустити", callback_data="power_type:skip")],
            [InlineKeyboardButton(text="❌ Відміна", callback_data="cancel_checklist")]
        ]
    )

def get_settings_keyboard(trader_pm: bool, trader_groups: bool, hide_not_working: bool = False, auto_close_shifts: bool = False, reminder_interval: int = 5, report_margin: int = 20) -> InlineKeyboardMarkup:
    """Generates an inline keyboard for toggling notification settings."""
    pm_status = "✅" if trader_pm else "❌"
    groups_status = "✅" if trader_groups else "❌"
    short_hide_status = "✅" if hide_not_working else "❌"
    shifts_status = "✅" if auto_close_shifts else "❌"
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"ЛС Трейдера: {pm_status}", 
                    callback_data=f"toggle_setting:notify_trader_pm:{'0' if trader_pm else '1'}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Групи об'єктів: {groups_status}", 
                    callback_data=f"toggle_setting:notify_trader_groups:{'0' if trader_groups else '1'}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Приховати 'Не працює' в Статус ГПУ: {short_hide_status}", 
                    callback_data=f"toggle_setting:hide_not_working_in_short:{'0' if hide_not_working else '1'}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Авто-закриття змін: {shifts_status}", 
                    callback_data=f"toggle_setting:auto_close_shifts:{'0' if auto_close_shifts else '1'}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⏱ Перевірка смен: {reminder_interval}хв",
                    callback_data="set_reminder_interval_list"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⏰ Запас звіту: {report_margin}хв",
                    callback_data="set_report_margin_list"
                )
            ],
            [
                InlineKeyboardButton(text="📅 Планувальник завдань", callback_data="open_scheduler_mgmt")
            ],
            [InlineKeyboardButton(text="Закрити", callback_data="close_admin_inline")]
        ]
    )

def get_report_margin_keyboard() -> InlineKeyboardMarkup:
    """Keyboard to select report reminder margin."""
    margins = [5, 10, 15, 20, 30, 45, 60]
    keyboard = []
    for m in margins:
        keyboard.append([InlineKeyboardButton(text=f"{m} хвилин", callback_data=f"set_rep_margin:{m}")])
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="open_settings")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_reminder_interval_keyboard() -> InlineKeyboardMarkup:
    """Keyboard to select reminder interval."""
    intervals = [1, 5, 10, 15, 30, 60]
    keyboard = []
    for i in intervals:
        keyboard.append([InlineKeyboardButton(text=f"{i} хвилин", callback_data=f"set_rem_int:{i}")])
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="open_settings")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_scheduler_mgmt_kb(jobs: list) -> InlineKeyboardMarkup:
    """Generates an inline keyboard for managing scheduler jobs."""
    keyboard = []
    for name, time_str, key, is_active in jobs:
        status_icon = "🟢" if is_active else "🔴"
        # Row with job name and time
        keyboard.append([InlineKeyboardButton(text=f"{status_icon} {name}: {time_str}", callback_data=f"edit_job:{key}")])
        # Row with toggle button
        toggle_text = "⏸ Призупинити" if is_active else "▶️ Активувати"
        toggle_val = "0" if is_active else "1"
        keyboard.append([
            InlineKeyboardButton(text=toggle_text, callback_data=f"toggle_job:{key}:{toggle_val}")
        ])
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад до налаштувань", callback_data="back_to_settings")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_scheduler_hour_kb() -> InlineKeyboardMarkup:
    """Generates an inline keyboard for hour selection for scheduler."""
    keyboard_rows = []
    for row_num in range(0, 24, 6):
        row = []
        for hour in range(row_num, min(row_num + 6, 24)):
            row.append(InlineKeyboardButton(text=f"{hour:02d}", callback_data=f"sched_h:{hour:02d}"))
        keyboard_rows.append(row)
    keyboard_rows.append([InlineKeyboardButton(text="Скасувати", callback_data="open_scheduler_mgmt")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

def get_scheduler_minute_kb(hour: str) -> InlineKeyboardMarkup:
    """Generates an inline keyboard for minute selection for scheduler."""
    keyboard_rows = []
    for row_num in range(0, 60, 20):
        row = []
        for minute in range(row_num, min(row_num + 20, 60), 5):
            row.append(InlineKeyboardButton(text=f"{minute:02d}", callback_data=f"sched_m:{hour}:{minute:02d}"))
        keyboard_rows.append(row)
    keyboard_rows.append([InlineKeyboardButton(text="⬅️ Назад до годин", callback_data="back_to_sched_hours")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

def get_parser_edit_objects_kb(parsed_data: list) -> InlineKeyboardMarkup:
    """Generates a list of objects for selection during parser editing."""
    keyboard = []
    for i, item in enumerate(parsed_data):
        display_name = re.sub(r"[\(\)]", "", item['db_name'])
        status = "❌" if item['is_not_working'] else "✅"
        keyboard.append([InlineKeyboardButton(text=f"{status} {display_name}", callback_data=f"pedit_obj:{i}")])
    
    keyboard.append([InlineKeyboardButton(text="✅ Все вірно, зберегти", callback_data="trader_parse_confirm")])
    keyboard.append([InlineKeyboardButton(text="❌ Відміна", callback_data="trader_parse_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_parser_edit_field_kb(idx: int, item: dict) -> InlineKeyboardMarkup:
    """Generates editing menu for a specific object."""
    keyboard = []
    
    # Toggle status button
    status_text = "🔄 Встановити: ПРАЦЮЄ" if item['is_not_working'] else "🔄 Встановити: НЕ ПРАЦЮЄ"
    keyboard.append([InlineKeyboardButton(text=status_text, callback_data=f"pedit_toggle_work:{idx}")])
    
    if not item['is_not_working']:
        # Power cycle (logic in handler)
        # We'll just show current power/mode
        pwr = item['intervals'][0]['power'] if item['intervals'] else 100
        mode = item['intervals'][0]['mode'] if item['intervals'] else "Мережа"
        
        keyboard.append([InlineKeyboardButton(text=f"⚡ Потужність: {pwr}%", callback_data=f"pedit_cycle_pwr:{idx}")])
        keyboard.append([InlineKeyboardButton(text=f"⚙️ Режим: {mode}", callback_data=f"pedit_cycle_mode:{idx}")])
        keyboard.append([InlineKeyboardButton(text="🕒 Змінити час", callback_data=f"pedit_input_time:{idx}")])

    keyboard.append([InlineKeyboardButton(text="⬅️ Назад до списку", callback_data="pedit_back_list")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# --- Broadcast Keyboards ---

def get_broadcast_main_kb() -> InlineKeyboardMarkup:
    """Main menu for broadcasts."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Створити розсилку", callback_data="bc_create")],
        [InlineKeyboardButton(text="📂 Архів розсилок", callback_data="bc_archive:0")],
        [InlineKeyboardButton(text="❌ Закрити", callback_data="close_admin_inline")]
    ])

def get_broadcast_preview_kb() -> InlineKeyboardMarkup:
    """Keyboard for previewing a broadcast."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Відправити", callback_data="bc_send:normal"),
            InlineKeyboardButton(text="📌 З закріпленням", callback_data="bc_send:pinned")
        ],
        [InlineKeyboardButton(text="❌ Відмінити", callback_data="bc_cancel")]
    ])

def get_broadcast_archive_kb(broadcasts: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Keyboard for broadcast archive with pagination."""
    keyboard = []
    for b in broadcasts:
        # Show first 30 chars of text or "Photo"
        label = (b['text'][:30] + "...") if b['text'] else "🖼 Фото-повідомлення"
        keyboard.append([InlineKeyboardButton(text=label, callback_data=f"bc_view:{b['id']}")])
    
    # Pagination
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"bc_archive:{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"bc_archive:{page+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
        
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="bc_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_broadcast_manage_kb(bc_id: int, is_pinned: bool) -> InlineKeyboardMarkup:
    """Keyboard for managing an existing broadcast."""
    pin_text = "📍 Відкріпити" if is_pinned else "📌 Закріпити"
    pin_action = "unpin" if is_pinned else "pin"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редагувати текст", callback_data=f"bc_edit:{bc_id}")],
        [InlineKeyboardButton(text=pin_text, callback_data=f"bc_pin:{bc_id}:{pin_action}")],
        [InlineKeyboardButton(text="🗑 Видалити розсилку", callback_data=f"bc_delete:{bc_id}")],
        [InlineKeyboardButton(text="⬅️ До архіву", callback_data="bc_archive:0")]
    ])

# --- Shift Keyboards ---

def get_predecessor_confirm_kb(object_id: int) -> InlineKeyboardMarkup:
    """Keyboard for the previous worker to confirm shift hand-over."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Так", callback_data=f"shift_handover:{object_id}:yes"),
                InlineKeyboardButton(text="❌ Ні", callback_data=f"shift_handover:{object_id}:no")
            ]
        ]
    )

def get_shift_action_confirm_kb(action: str, object_id: int) -> InlineKeyboardMarkup:
    """Final confirmation before starting or ending a shift."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Так, впевнений", callback_data=f"shift_act:{action}:{object_id}"),
                InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_checklist")
            ]
        ]
    )
