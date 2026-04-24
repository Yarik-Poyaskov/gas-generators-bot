from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import re
import logging

from app.config import config
from app.filters.is_admin import IsAdmin
from app.db.database import (
    get_reports_by_date, get_report_by_id, update_report_field, delete_report_by_id
)
from app.states.admin_edit import AdminEditState
from app.keyboards.inline import (
    get_edit_report_date_kb, get_report_list_kb, get_report_actions_kb, 
    get_report_fields_kb, get_edit_work_mode_kb, get_edit_gpu_status_kb,
    get_hour_selection_kb, get_minute_selection_kb, get_confirmation_kb
)

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

logger = logging.getLogger(__name__)

# --- Вход в режим редактирования ---

@router.message(F.text == "Перегляд та коригування Чек-Листів")
async def cmd_admin_edit_reports(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(AdminEditState.waiting_for_date)
    await message.answer(
        "🔎 **Коригування Чек-Листів**\n\nОберіть дату для перегляду звітів:",
        reply_markup=get_edit_report_date_kb()
    )

@router.callback_query(AdminEditState.waiting_for_date, F.data.startswith("edit_date:"))
async def process_date_selection(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[1]
    
    if action == "today":
        date_str = datetime.now().strftime("%Y-%m-%d")
    elif action == "yesterday":
        date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    elif action == "calendar":
        await callback.answer("Функція календаря в розробці. Оберіть 'Сьогодні' или 'Вчора'", show_alert=True)
        return
    else:
        await callback.answer()
        return

    await state.update_data(edit_date=date_str, edit_page=0)
    await show_reports_list(callback, state, date_str, 0)
    await callback.answer()

async def show_reports_list(callback_or_message, state: FSMContext, date_str: str, page: int):
    reports = await get_reports_by_date(date_str)
    
    if not reports:
        msg = f"Звітів за {date_str} не знайдено."
        if isinstance(callback_or_message, CallbackQuery):
            await callback_or_message.message.edit_text(msg, reply_markup=get_edit_report_date_kb())
        else:
            await callback_or_message.answer(msg, reply_markup=get_edit_report_date_kb())
        return

    per_page = 10
    total_pages = (len(reports) + per_page - 1) // per_page
    start_idx = page * per_page
    end_idx = start_idx + per_page
    current_reports = reports[start_idx:end_idx]

    kb = get_report_list_kb(current_reports, page, total_pages)
    
    text = f"📋 **Звіти за {date_str}**\nЗнайдено: {len(reports)}\nОберіть об'єкт для перегляду:"
    
    if isinstance(callback_or_message, CallbackQuery):
        await callback_or_message.message.edit_text(text, reply_markup=kb)
    else:
        await callback_or_message.answer(text, reply_markup=kb)
    
    await state.set_state(AdminEditState.waiting_for_report_selection)

@router.callback_query(AdminEditState.waiting_for_report_selection, F.data.startswith("edit_reports_page:"))
async def process_reports_pagination(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[1])
    data = await state.get_data()
    date_str = data.get('edit_date')
    await state.update_data(edit_page=page)
    await show_reports_list(callback, state, date_str, page)
    await callback.answer()

@router.callback_query(F.data == "back_to_edit_date")
async def back_to_date_selection(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminEditState.waiting_for_date)
    await callback.message.edit_text(
        "🔎 **Коригування Чек-Листів**\n\nОберіть дату для перегляду звітів:",
        reply_markup=get_edit_report_date_kb()
    )
    await callback.answer()

# --- Просмотр конкретного отчета ---

@router.callback_query(AdminEditState.waiting_for_report_selection, F.data.startswith("edit_report:"))
async def process_report_selection(callback: CallbackQuery, state: FSMContext):
    report_id = int(callback.data.split(":")[1])
    await state.update_data(current_report_id=report_id)
    await show_report_view(callback, state, report_id)
    await callback.answer()

from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

KYIV_TZ = ZoneInfo("Europe/Kiev")

async def show_report_view(callback: CallbackQuery, state: FSMContext, report_id: int):
    report = await get_report_by_id(report_id)
    if not report:
        await callback.answer("Звіт не знайдено!", show_alert=True)
        return

    # Convert created_at from UTC to Kyiv time
    try:
        dt_utc = datetime.strptime(report['created_at'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        local_time = dt_utc.astimezone(KYIV_TZ)
        created_at_display = local_time.strftime("%Y-%m-%d %H:%M:%S")
    except:
        created_at_display = report['created_at']

    text = f"📄 **Перегляд звіту #{report_id}**\n"
    text += f"📍 Об'єкт: {report['tc_name']}\n"
    text += f"👤 Подав: {report['full_name']}\n"
    text += f"🕒 Створено: {created_at_display}\n\n"
    
    fields = [
        ('work_mode', '1. Режим'),
        ('start_time', '2. Час запуску'),
        ('gpu_status', '4. Статус ГПУ'),
        ('battery_voltage', '5. АКБ'),
        ('pressure_before', '6. Тиск До'),
        ('pressure_after', '7. Тиск Після'),
        ('total_mwh', '8. Виробітка (МВт)'),
        ('total_hours', '9. Мотогодини'),
        ('oil_sampling_limit', '10. Ліміт мастила')
    ]
    
    for f_id, f_name in fields:
        val = report.get(f_id)
        text += f"<b>{f_name}:</b> {val if val is not None else '---'}\n"

    await callback.message.edit_text(text, reply_markup=get_report_actions_kb(report_id), parse_mode="HTML")
    await state.set_state(AdminEditState.waiting_for_report_action)

@router.callback_query(F.data == "back_to_report_list")
async def back_to_report_list(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    date_str = data.get('edit_date')
    page = data.get('edit_page', 0)
    await show_reports_list(callback, state, date_str, page)
    await callback.answer()

# --- Выбор поля для редактирования ---

@router.callback_query(AdminEditState.waiting_for_report_action, F.data.startswith("edit_fields:"))
async def process_edit_fields_selection(callback: CallbackQuery, state: FSMContext):
    report_id = int(callback.data.split(":")[1])
    report = await get_report_by_id(report_id)
    
    await callback.message.edit_text(
        f"✏️ **Редагування звіту #{report_id}**\n📍 {report['tc_name']}\n\nОберіть параметр для зміни:",
        reply_markup=get_report_fields_kb(report)
    )
    await state.set_state(AdminEditState.waiting_for_parameter_selection)
    await callback.answer()

@router.callback_query(F.data.startswith("back_to_report_view:"))
async def back_to_report_view(callback: CallbackQuery, state: FSMContext):
    report_id = int(callback.data.split(":")[1])
    await show_report_view(callback, state, report_id)
    await callback.answer()

# --- Редактирование конкретного поля ---

@router.callback_query(AdminEditState.waiting_for_parameter_selection, F.data.startswith("edit_field:"))
async def process_field_selection(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split(":")[1]
    data = await state.get_data()
    report_id = data.get('current_report_id')
    report = await get_report_by_id(report_id)
    
    await state.update_data(editing_field=field, old_value=report.get(field))
    
    field_names = {
        'work_mode': 'Режим роботи',
        'start_time': 'Час запуску',
        'gpu_status': 'Статус ГПУ',
        'battery_voltage': 'Напруга АКБ',
        'pressure_before': 'Тиск До',
        'pressure_after': 'Тиск Після',
        'total_mwh': 'Виробітка (МВт)',
        'total_hours': 'Мотогодини',
        'oil_sampling_limit': 'Ліміт мастила'
    }
    
    prompt = f"✏️ **Зміна параметра: {field_names.get(field)}**\n"
    prompt += f"📍 Об'єкт: {report['tc_name']}\n"
    prompt += f"ℹ️ Поточне значення: `{report.get(field)}`\n\n"
    prompt += "Оберіть нове значення або введіть вручну (якщо це число):"
    
    if field == 'work_mode':
        await callback.message.edit_text(prompt, reply_markup=get_edit_work_mode_kb(), parse_mode="Markdown")
    elif field == 'gpu_status':
        await callback.message.edit_text(prompt, reply_markup=get_edit_gpu_status_kb(), parse_mode="Markdown")
    elif field == 'start_time':
        await callback.message.edit_text(prompt, reply_markup=get_hour_selection_kb(), parse_mode="Markdown")
    else:
        await callback.message.edit_text(prompt + "\n\n(Введіть значення повідомленням)", parse_mode="Markdown")
    
    await state.set_state(AdminEditState.waiting_for_new_value)
    await callback.answer()

# --- Обработка новых значений ---

@router.callback_query(AdminEditState.waiting_for_new_value, F.data.startswith("set_val:"))
async def process_callback_value(callback: CallbackQuery, state: FSMContext):
    _, field, val = callback.data.split(":")
    await save_and_notify(callback, state, field, val)
    await callback.answer()

@router.callback_query(AdminEditState.waiting_for_new_value, F.data.startswith("select_hour_"))
async def process_hour_selection(callback: CallbackQuery, state: FSMContext):
    hour = callback.data.split("_")[2]
    await callback.message.edit_reply_markup(reply_markup=get_minute_selection_kb(int(hour)))
    await callback.answer()

@router.callback_query(AdminEditState.waiting_for_new_value, F.data.startswith("select_minute_"))
async def process_minute_selection(callback: CallbackQuery, state: FSMContext):
    _, _, hour, minute = callback.data.split("_")
    val = f"{hour}:{minute}"
    await save_and_notify(callback, state, 'start_time', val)
    await callback.answer()

@router.callback_query(AdminEditState.waiting_for_new_value, F.data == "back_to_hours")
async def back_to_hours(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=get_hour_selection_kb())
    await callback.answer()

@router.message(AdminEditState.waiting_for_new_value)
async def process_text_value(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data.get('editing_field')
    val = message.text.strip().replace(",", ".")
    
    # Simple validation for numeric fields
    numeric_fields = ['pressure_before', 'pressure_after', 'total_mwh', 'total_hours', 'oil_sampling_limit']
    if field in numeric_fields:
        try:
            val = float(val)
        except ValueError:
            await message.answer("Помилка! Будь ласка, введіть число.")
            return

    await save_and_notify(message, state, field, val)

async def save_and_notify(event, state: FSMContext, field: str, val: any):
    data = await state.get_data()
    report_id = data.get('current_report_id')
    old_val = data.get('old_value')
    
    await update_report_field(report_id, field, val)
    
    # Log the action
    admin_name = event.from_user.full_name
    admin_id = event.from_user.id
    log_msg = f"Admin {admin_name} ({admin_id}) changed field '{field}' in report #{report_id} from '{old_val}' to '{val}'"
    logger.info(log_msg)
    with open("user_actions.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()}: {log_msg}\n")
        
    msg_text = f"✅ **Дані успішно оновлено!**\n\n🔄 Змінено: `{old_val}` ➡️ `{val}`\n\n⚠️ **Важливо:** Не забудьте виправити дані в Google Таблиці вручну."
    
    if isinstance(event, CallbackQuery):
        await event.message.answer(msg_text, parse_mode="Markdown")
        await show_report_view(event, state, report_id)
    else:
        await event.answer(msg_text, parse_mode="Markdown")
        # To show report view after text message, we need to send a new one
        report = await get_report_by_id(report_id)
        await event.answer(f"Звіт #{report_id} оновлено.", reply_markup=get_report_actions_kb(report_id))
        await state.set_state(AdminEditState.waiting_for_report_action)

@router.callback_query(F.data == "back_to_fields")
async def back_to_fields(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    report_id = data.get('current_report_id')
    report = await get_report_by_id(report_id)
    await callback.message.edit_text(
        f"✏️ **Редагування звіту #{report_id}**\n📍 {report['tc_name']}\n\nОберіть параметр для зміни:",
        reply_markup=get_report_fields_kb(report)
    )
    await state.set_state(AdminEditState.waiting_for_parameter_selection)
    await callback.answer()

# --- Удаление отчета ---

@router.callback_query(AdminEditState.waiting_for_report_action, F.data.startswith("delete_report:"))
async def process_delete_start(callback: CallbackQuery, state: FSMContext):
    report_id = int(callback.data.split(":")[1])
    await state.update_data(delete_report_id=report_id)
    await callback.message.edit_text(
        f"❓ **Ви впевнені, що хочете видалити звіт #{report_id}?**",
        reply_markup=get_confirmation_kb("confirm_delete_1", "back_to_report_list")
    )
    await state.set_state(AdminEditState.waiting_for_delete_confirm1)
    await callback.answer()

@router.callback_query(AdminEditState.waiting_for_delete_confirm1, F.data == "confirm_delete_1")
async def process_delete_confirm2(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    report_id = data.get('delete_report_id')
    await callback.message.edit_text(
        f"⚠️ **Ця дія незворотня!**\nПідтвердіть видалення звіту #{report_id} ще раз:",
        reply_markup=get_confirmation_kb("confirm_delete_final", "back_to_report_list")
    )
    await state.set_state(AdminEditState.waiting_for_delete_confirm2)
    await callback.answer()

@router.callback_query(AdminEditState.waiting_for_delete_confirm2, F.data == "confirm_delete_final")
async def process_delete_final(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    report_id = data.get('delete_report_id')
    
    await delete_report_by_id(report_id)
    
    # Log
    admin_name = callback.from_user.full_name
    log_msg = f"Admin {admin_name} DELETED report #{report_id}"
    logger.info(log_msg)
    with open("user_actions.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()}: {log_msg}\n")
        
    await callback.message.edit_text(f"✅ Звіт #{report_id} успішно видалено.")
    
    # Return to list
    date_str = data.get('edit_date')
    page = data.get('edit_page', 0)
    await show_reports_list(callback, state, date_str, page)
    await callback.answer()

@router.callback_query(F.data == "cancel_checklist")
async def process_cancel_universal(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Дію скасовано.")
    await callback.answer()
