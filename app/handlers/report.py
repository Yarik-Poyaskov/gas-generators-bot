import re
import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery, InlineKeyboardMarkup, InputMediaPhoto
from datetime import datetime

from app.config import config
from app.db.database import (
    add_report, get_user, get_user_objects_by_tg_id, get_all_objects, get_object_by_id, get_setting
)
from export_to_google import export_to_google
from app.filters.is_admin import IsAdmin
from app.keyboards.inline import (
    get_apparatus_check_kb, get_hour_selection_kb, get_minute_selection_kb,
    get_object_selection_kb, get_report_confirm_kb, get_launch_planned_kb,
    get_planned_work_mode_kb, get_time_type_kb, get_power_type_kb, get_skip_after_pressure_kb,
    get_short_power_type_kb, get_planned_power_type_kb, get_only_skip_power_kb,
    get_short_stop_power_kb
)
from app.keyboards.reply import (
    get_work_mode_kb, get_gpu_status_kb, get_cancel_keyboard, get_main_menu_keyboard, 
    get_simple_cancel_kb, get_is_gpu_working_kb, get_work_mode_active_kb, get_work_mode_not_active_kb,
    get_gpu_status_active_kb, get_gpu_status_not_active_kb, get_work_mode_short_kb,
    get_gpu_status_short_launch_kb, get_gpu_status_short_stop_kb
)
from app.states.report import ReportState

router = Router()

def get_status_emoji(gpu_status: str, work_mode: str = "") -> str:
    """Returns status emoji based on text."""
    status_lower = (gpu_status or "").lower()
    mode_lower = (work_mode or "").lower()
    
    if "аварії" in status_lower or "не готова" in status_lower or "аварії" in mode_lower or "не готова" in mode_lower or "аваріями" in status_lower:
        return "⚠️"
    if "стабільна" in status_lower:
        return "🟢"
    if "не працює" in status_lower or "не працює" in mode_lower:
        return "🔴"
    return "✅"

# --- Common Handlers ---

@router.message(F.text == "Відміна", F.chat.type == "private")
async def cmd_cancel_report(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await get_user(user_id)
    is_admin = user_id in config.admin_ids
    role = user_data['role'] if user_data else 'user'
    await state.clear()
    await message.answer("Дію скасовано.", reply_markup=get_main_menu_keyboard(is_admin=is_admin, role=role))

@router.callback_query(F.data == "cancel_checklist")
async def handle_cancel_checklist_inline(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_data = await get_user(user_id)
    is_admin = user_id in config.admin_ids
    role = user_data['role'] if user_data else 'user'
    await state.clear()
    if callback.message:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer("Дію скасовано.", reply_markup=get_main_menu_keyboard(is_admin=is_admin, role=role))
    await callback.answer()

# --- Start Handlers ---

@router.message(F.text == "Статус ГПУ", F.chat.type == "private")
async def start_short_report(message: Message, state: FSMContext):
    await init_report(message, state, is_short=True)

@router.message(F.text == "Подати чек-лист", F.chat.type == "private")
async def start_report_button(message: Message, state: FSMContext):
    await start_report(message, state)

@router.message(Command("report"), F.chat.type == "private")
async def start_report(message: Message, state: FSMContext):
    await init_report(message, state, is_short=False)

async def init_report(message: Message, state: FSMContext, is_short: bool):
    user_id = message.from_user.id
    user_data = await get_user(user_id)
    is_admin = user_id in config.admin_ids
    if not user_data and not is_admin:
        await message.answer("Доступ заборонено.")
        return

    await state.clear()
    await state.update_data(
        is_short=is_short, user_id=user_id, 
        username=message.from_user.username or "none",
        full_name=user_data['full_name'] if user_data else message.from_user.full_name
    )
    
    user_objs = await get_user_objects_by_tg_id(user_id)
    if not user_objs and is_admin:
        user_objs = await get_all_objects()
    
    if not user_objs:
        await message.answer("Вам не призначено жодного об'єкта.", reply_markup=get_main_menu_keyboard(is_admin=is_admin))
        return

    if len(user_objs) == 1:
        obj = user_objs[0]
        await state.update_data(obj_id=obj['id'], tc_name=obj['name'])
        suffix = " (Скорочений)" if is_short else ""
        
        if is_short:
            # Default to True for short report, will be updated in work_mode handler if needed
            await state.update_data(is_gpu_working=True)
            hide_not_working = await get_setting('hide_not_working_in_short', '0') == '1'
            await state.set_state(ReportState.work_mode)
            await message.answer(f"Об'єкт: <b>{obj['name']}</b>{suffix}\n\n1. Режим роботи ГПУ?", reply_markup=get_cancel_keyboard(get_work_mode_short_kb(hide_not_working)))
        else:
            await state.set_state(ReportState.is_gpu_working)
            await message.answer(f"Об'єкт: <b>{obj['name']}</b>{suffix}\n\nЧи працює зараз ГПУ?", reply_markup=get_cancel_keyboard(get_is_gpu_working_kb()))
    else:
        await state.set_state(ReportState.selecting_object)
        await message.answer("Оберіть об'єкт:", reply_markup=get_object_selection_kb(user_objs, page=0, per_page=config.users_per_page))

# --- Pagination & Selection ---

@router.callback_query(F.data.startswith("sel_obj_page:"))
async def process_sel_obj_pagination(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    user_objs = await get_user_objects_by_tg_id(user_id)
    if not user_objs and user_id in config.admin_ids:
        user_objs = await get_all_objects()
    await callback.message.edit_reply_markup(reply_markup=get_object_selection_kb(user_objs, page=page, per_page=config.users_per_page))
    await callback.answer()

@router.callback_query(ReportState.selecting_object, F.data.startswith("select_obj:"))
async def process_object_selection(callback: CallbackQuery, state: FSMContext):
    obj_id = int(callback.data.split(":")[1])
    obj = await get_object_by_id(obj_id)
    if not obj:
        await callback.answer("Об'єкт не знайдено.")
        return
    await state.update_data(obj_id=obj_id, tc_name=obj['name'])
    data = await state.get_data()
    is_short = data.get("is_short", False)
    suffix = " (Скорочений)" if is_short else ""
    
    if is_short:
        # Default to True for short report, will be updated in work_mode handler if needed
        await state.update_data(is_gpu_working=True)
        hide_not_working = await get_setting('hide_not_working_in_short', '0') == '1'
        await state.set_state(ReportState.work_mode)
        if callback.message:
            try:
                await callback.message.delete()
            except Exception: pass
            await callback.message.answer(f"Об'єкт: <b>{obj['name']}</b>{suffix}\n\n1. Режим роботи ГПУ?", reply_markup=get_cancel_keyboard(get_work_mode_short_kb(hide_not_working)))
    else:
        await state.set_state(ReportState.is_gpu_working)
        if callback.message:
            try:
                await callback.message.delete()
            except Exception: pass
            await callback.message.answer(f"Об'єкт: <b>{obj['name']}</b>{suffix}\n\nЧи працює зараз ГПУ?", reply_markup=get_cancel_keyboard(get_is_gpu_working_kb()))
    await callback.answer()

# --- New Is Working Handler ---

@router.message(ReportState.is_gpu_working, F.text.in_(["✅ ГПУ зараз працює", "⛔️ ГПУ зараз НЕ працює"]))
async def handle_is_gpu_working(message: Message, state: FSMContext):
    is_working = message.text == "✅ ГПУ зараз працює"
    await state.update_data(is_gpu_working=is_working)
    await state.set_state(ReportState.work_mode)
    
    if is_working:
        await message.answer("1. Режим роботи ГПУ?", reply_markup=get_cancel_keyboard(get_work_mode_active_kb()))
    else:
        await message.answer("1. Режим роботи ГПУ?", reply_markup=get_cancel_keyboard(get_work_mode_not_active_kb()))

@router.message(ReportState.is_gpu_working)
async def handle_is_gpu_working_invalid(message: Message, state: FSMContext):
    await message.answer(
        "Будь ласка, оберіть варіант за допомогою кнопок:\n"
        "✅ ГПУ зараз працює або ⛔️ ГПУ зараз НЕ працює",
        reply_markup=get_cancel_keyboard(get_is_gpu_working_kb())
    )

# --- Report Flow ---

@router.message(ReportState.work_mode, F.text.in_(["Острів", "Мережа"]))
async def set_work_mode_active(message: Message, state: FSMContext):
    data = await state.get_data()
    # Security check: if user said GPU is NOT working, they shouldn't be able to select Island/Grid
    # We only apply this check if it's NOT a short report, because in short reports we default is_gpu_working to True
    if not data.get("is_short") and not data.get("is_gpu_working", True):
        await message.answer(
            "Ви вказали, що ГПУ <b>НЕ працює</b>. Будь ласка, оберіть відповідний статус:",
            reply_markup=get_cancel_keyboard(get_work_mode_not_active_kb())
        )
        return

    # For short report, ensure is_gpu_working is True when choosing active mode
    if data.get("is_short"):
        await state.update_data(is_gpu_working=True)

    await state.update_data(work_mode=message.text)
    if data.get("is_short"):
        await state.set_state(ReportState.time_type)
        await message.answer("Оберіть тип часу:", reply_markup=get_time_type_kb())
    else:
        await state.set_state(ReportState.start_time)
        await message.answer("2. Оберіть годину запуску ГПУ:", reply_markup=get_hour_selection_kb(is_not_working=False))

@router.callback_query(ReportState.time_type, F.data.startswith("time_type:"))
async def handle_time_type_selection(callback: CallbackQuery, state: FSMContext):
    label = callback.data.split(":")[1]
    await state.update_data(time_label=label)
    await state.set_state(ReportState.start_time)
    
    data = await state.get_data()
    work_mode = (data.get("work_mode") or "").lower()
    # If mode contains "Не працює", "аварії" or "не готова", then is_not_working should be True
    is_not_working = any(x in work_mode for x in ["не працює", "аварії", "не готова"])
    
    await callback.message.edit_text(f"Обрано: {label}\n\nОберіть години:", reply_markup=get_hour_selection_kb(is_not_working=is_not_working))
    await callback.answer()

@router.message(ReportState.work_mode, F.text.in_(["Не працює, готова до пуску", "ГПУ в аварії, не готова до пуску.", "Не працює"]))
async def set_work_mode_not_ready(message: Message, state: FSMContext):
    data = await state.get_data()
    # Security check: if user said GPU IS working, they shouldn't be able to select "Not working"
    # Skip check for short reports
    if not data.get("is_short") and data.get("is_gpu_working", False):
        await message.answer(
            "Ви вказали, що ГПУ <b>працює</b>. Будь ласка, оберіть відповідний режим:",
            reply_markup=get_cancel_keyboard(get_work_mode_active_kb())
        )
        return

    # For short report, ensure is_gpu_working is False when choosing not working mode
    if data.get("is_short"):
        await state.update_data(is_gpu_working=False)

    mode_text = message.text
    if mode_text == "Не працює":
        mode_text = "Не працює, готова до пуску"
    await state.update_data(work_mode=mode_text)
    await state.set_state(ReportState.is_launch_planned)
    await message.answer("Чи планується запуск ГПУ на поточну дату?", reply_markup=get_launch_planned_kb())

@router.message(ReportState.work_mode)
async def handle_work_mode_invalid(message: Message, state: FSMContext):
    data = await state.get_data()
    is_working = data.get("is_gpu_working", True)
    if is_working:
        kb = get_work_mode_active_kb()
    else:
        kb = get_work_mode_not_active_kb()
    
    await message.answer(
        "Будь ласка, оберіть варіант з клавіатури або натисніть 'Відміна'.",
        reply_markup=get_cancel_keyboard(kb)
    )

@router.callback_query(ReportState.is_launch_planned, F.data == "launch_planned_yes")
async def handle_launch_planned_yes(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReportState.start_time)
    await callback.message.edit_text("2. Оберіть годину планового запуску ГПУ:", reply_markup=get_hour_selection_kb(is_not_working=False))
    await callback.answer()

@router.callback_query(ReportState.is_launch_planned, F.data == "launch_planned_no")
async def handle_launch_planned_no(callback: CallbackQuery, state: FSMContext):
    # If not planned, we skip time but keep the selected work mode for the report
    data = await state.get_data()
    is_short = data.get("is_short", False)
    await state.update_data(start_time="—")
    await state.set_state(ReportState.power_type)
    
    # If no launch is planned, only "Skip" power makes sense (no Current or Planned power)
    markup = get_only_skip_power_kb()
    await callback.message.edit_text("Відмічено, що на поточную дату запуск не планується.\n\n3. Оберіть тип потужності:", reply_markup=markup)
    await callback.answer()

@router.callback_query(ReportState.start_time, F.data.startswith("select_hour_"))
async def handle_hour_selection(callback: CallbackQuery, state: FSMContext):
    hour = int(callback.data.split("_")[2])
    await state.update_data(selected_hour=hour)
    await callback.message.edit_text(f"Годину обрано: {hour:02d}. Оберіть хвилини:", reply_markup=get_minute_selection_kb(hour))
    await callback.answer()

@router.callback_query(ReportState.start_time, F.data.startswith("select_minute_"))
async def handle_minute_selection(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    hour, minute = int(parts[2]), int(parts[3])
    data = await state.get_data()
    time_str = f"{hour:02d}:{minute:02d}"
    
    # If mode is one of the "not working" types but launch is planned
    if "не готова" in data.get("work_mode") or "готова до пуску" in data.get("work_mode"):
        time_str = f"Плановий - {time_str}"

    await state.update_data(start_time=time_str)

    if data.get("is_short"):
        await state.set_state(ReportState.power_type)
        time_label = data.get("time_label", "")
        
        # If short report and Stop Time selected, show only Skip/Cancel
        if "Час зупинки" in time_label:
            markup = get_short_stop_power_kb()
        elif "не готова" in data.get("work_mode") or "готова до пуску" in data.get("work_mode"):
            markup = get_planned_power_type_kb()
        else:
            markup = get_short_power_type_kb()
            
        await callback.message.edit_text(f"Час: {time_str}.\n\n3. Оберіть тип потужності:", reply_markup=markup)
    elif "не готова" in data.get("work_mode") or "готова до пуску" in data.get("work_mode"):
        await state.set_state(ReportState.planned_work_mode)
        await callback.message.edit_text(f"Час: {time_str}.\n\nОберіть плановий режим роботи:", reply_markup=get_planned_work_mode_kb())
    else:
        await state.set_state(ReportState.power_type)
        # await callback.message.edit_text(f"Час: {time_str}.\n\n3. Оберіть тип потужності:", reply_markup=get_power_type_kb())
        await callback.message.edit_text(f"Час: {time_str}.\n\n3. Оберіть тип потужності:", reply_markup=get_short_power_type_kb())
    await callback.answer()

@router.callback_query(ReportState.planned_work_mode, F.data.startswith("planned_mode:"))
async def handle_planned_mode_selection(callback: CallbackQuery, state: FSMContext):
    mode = callback.data.split(":")[1]
    # Update work_mode to include planned target
    data = await state.get_data()
    current_mode = data.get("work_mode")
    await state.update_data(work_mode=f"{current_mode} (Плановий режим: {mode})")
    await state.set_state(ReportState.power_type)
    
    # If a launch is planned, "Current" power makes no sense, only "Planned"
    markup = get_planned_power_type_kb()
    await callback.message.edit_text(f"Плановий режим: {mode}.\n\n3. Оберіть тип потужності:", reply_markup=markup)
    await callback.answer()

@router.callback_query(ReportState.power_type, F.data.startswith("power_type:"))
async def handle_power_type_selection(callback: CallbackQuery, state: FSMContext):
    ptype = callback.data.split(":")[1]
    data = await state.get_data()
    is_short = data.get("is_short", False)
    is_working = data.get("is_gpu_working", True)
    
    if ptype == "skip":
        await state.update_data(power_label="-", load_power_percent="-", load_power_kw="-")
        await state.set_state(ReportState.gpu_status)
        if callback.message:
            try:
                await callback.message.delete()
            except Exception: pass
        
        if is_short:
            time_label = data.get("time_label", "")
            if "Час зупинки" in time_label:
                kb = get_gpu_status_short_stop_kb()
            else:
                kb = get_gpu_status_short_launch_kb()
        else:
            kb = get_gpu_status_active_kb() if is_working else get_gpu_status_not_active_kb()
            
        await callback.message.answer("Потужність пропущено.\n\n4. Статус роботи ГПУ?", reply_markup=get_cancel_keyboard(kb))
    else:
        await state.update_data(power_label=ptype)
        await state.set_state(ReportState.load_power_percent)
        await callback.message.edit_text(f"Тип потужності: {ptype}.\n\n3.1 Введіть навантаження в %:")
    await callback.answer()

@router.message(ReportState.load_power_percent)
async def set_load_power_percent(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Будь ласка, введіть число (наприклад: 50.5)")
        return
    try:
        val = float(message.text.replace(",", "."))
        await state.update_data(load_power_percent=val)
        await state.set_state(ReportState.load_power_kw)
        await message.answer("3.2 Введіть навантаження в кВт", reply_markup=get_simple_cancel_kb())
    except ValueError:
        await message.answer("Введіть число.")

@router.message(ReportState.load_power_kw)
async def set_load_power_kw(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Будь ласка, введіть число (наприклад: 1200)")
        return
    try:
        val = float(message.text.replace(",", "."))
        await state.update_data(load_power_kw=val)
        await state.set_state(ReportState.gpu_status)
        
        data = await state.get_data()
        is_short = data.get("is_short", False)
        is_working = data.get("is_gpu_working", True)
        time_label = data.get("time_label", "")
        
        if is_short:
            if "Час зупинки" in time_label:
                kb = get_gpu_status_short_stop_kb()
            else:
                kb = get_gpu_status_short_launch_kb()
        else:
            kb = get_gpu_status_active_kb() if is_working else get_gpu_status_not_active_kb()
        
        await message.answer("4. Статус роботи ГПУ?", reply_markup=get_cancel_keyboard(kb))
    except ValueError:
        await message.answer("Введіть число.")

@router.message(ReportState.gpu_status)
async def set_gpu_status(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Будь ласка, оберіть статус кнопкою або введіть текст.")
        return
    await state.update_data(gpu_status=message.text)
    data = await state.get_data()
    if data.get("is_short"):
        await show_final_confirmation(message, state)
    else:
        await state.set_state(ReportState.battery_voltage)
        await message.answer("5. Напруга АКБ (напр. '24/26 В')", reply_markup=get_simple_cancel_kb())

@router.message(ReportState.battery_voltage)
async def set_battery_voltage(message: Message, state: FSMContext):
    # 0. Check if text exists (prevents error if user sends a photo instead)
    if not message.text:
        await message.answer(
            "⚠️ Будь ласка, введіть напругу <b>цифрами</b>.\n"
            "Фотографії ми попросимо надіслати в самому кінці звіту.\n\n"
            "Приклад: 24.5/25.1\n"
            "Введіть ще раз 5. Напруга АКБ:"
        )
        return

    # 1. Find all numbers (integer or float with . or ,)
    nums = re.findall(r"(\d+(?:[.,]\d+)?)", message.text)

    if not nums:
        await message.answer(
            "⚠️ Некоректний формат.\n"
            "Будь ласка, введіть напругу цифрами.\n"
            "Приклад: 24.5/25.1 або 24,5 25,1\n\n"
            "Введіть ще раз 5. Напруга АКБ:"
        )
        return

    formatted_parts = []
    for n in nums:
        try:
            val = float(n.replace(',', '.'))
            formatted_parts.append(f"{val:.2f}".replace('.', ','))
        except ValueError:
            continue

    if not formatted_parts:
        await message.answer("❌ Не вдалося розпізнати числа. Спробуйте ще раз.")
        return

    # If only one number provided, we repeat it to match the XX,XX/XX,XX format
    if len(formatted_parts) == 1:
        final_val = f"{formatted_parts[0]}/{formatted_parts[0]}"
    else:
        final_val = "/".join(formatted_parts)

    await state.update_data(battery_voltage=final_val)
    await state.set_state(ReportState.pressure_before)
    await message.answer("6. Тиск антифризу до пуску ГПУ (GK, до насоса) в бар", reply_markup=get_simple_cancel_kb())

@router.message(ReportState.pressure_before)
async def set_pressure_before(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Будь ласка, введіть число.")
        return
    try:
        val = float(message.text.replace(",", "."))
        await state.update_data(pressure_before=val)
        await state.set_state(ReportState.pressure_after)
        await message.answer(
            "7. Тиск антифризу після пуску ГПУ (GK, до насоса) в бар", 
            reply_markup=get_skip_after_pressure_kb()
        )
    except ValueError:
        await message.answer("Введіть число.")

@router.callback_query(ReportState.pressure_after, F.data == "skip_pressure_after")
async def handle_skip_pressure_after(callback: CallbackQuery, state: FSMContext):
    await state.update_data(pressure_after="-")
    await state.set_state(ReportState.total_mwh)
    if callback.message:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            "7. Тиск антифризу після пуску ГПУ (GK, до насоса) в бар: -\n\n8. Всього вироблено (МВт*год):", 
            reply_markup=get_simple_cancel_kb()
        )
    await callback.answer()

@router.message(ReportState.pressure_after)
async def set_pressure_after(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Будь ласка, введіть число або '-'")
        return
    val = message.text.strip()
    if val == "-":
        await state.update_data(pressure_after="-")
    else:
        try:
            await state.update_data(pressure_after=float(val.replace(",", ".")))
        except ValueError:
            await message.answer("Введіть число або '-'")
            return
    await state.set_state(ReportState.total_mwh)
    await message.answer("8. Всього вироблено (МВт*год):", reply_markup=get_simple_cancel_kb())

@router.message(ReportState.total_mwh)
async def set_total_mwh(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Будь ласка, введіть число.")
        return
    try:
        val = float(message.text.replace(",", "."))
        await state.update_data(total_mwh=val)
        await state.set_state(ReportState.total_hours)
        await message.answer("9. Всього відпрацьовано (м/год):", reply_markup=get_simple_cancel_kb())
    except ValueError:
        await message.answer("Введіть число.")

@router.message(ReportState.total_hours)
async def set_total_hours(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Будь ласка, введіть число.")
        return
    try:
        val = float(message.text.replace(",", "."))
        await state.update_data(total_hours=val)
        await state.set_state(ReportState.oil_sampling_limit)
        await message.answer("10. До відбору оливи залишилося (м/год):", reply_markup=get_simple_cancel_kb())
    except ValueError:
        await message.answer("Введіть число.")

@router.message(ReportState.oil_sampling_limit)
async def set_oil_sampling_limit(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Будь ласка, введіть число.")
        return
    try:
        val = float(message.text.replace(",", "."))
        await state.update_data(oil_sampling_limit=val)
        await state.set_state(ReportState.apparatus_check)
        await message.answer("11. Звірка положення всіх комутаційних апаратів (ВК ГПУ, Т-1, Т-2, ВВ ГПУ, Ввод-1, Ввод-2, КЛ-1, КЛ-2, СВ-0,4 кВ). Все на своїх місцях?", reply_markup=get_apparatus_check_kb())
    except ValueError:
        await message.answer("Введіть число.")

@router.callback_query(ReportState.apparatus_check, F.data == "apparatus_checked")
async def process_apparatus_check(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReportState.photo_multimeter)
    await callback.message.edit_text("✅ Підтверджено. Надішліть фото мультиметра:")
    await callback.answer()

@router.message(ReportState.photo_multimeter, F.photo)
async def set_photo_multimeter(message: Message, state: FSMContext):
    await state.update_data(photo_multimeter_id=message.photo[-1].file_id)
    await state.set_state(ReportState.photo_shos)
    await message.answer("Надішліть фото ШОС (монітор):", reply_markup=get_simple_cancel_kb())

@router.message(ReportState.photo_multimeter)
async def set_photo_multimeter_invalid(message: Message, state: FSMContext):
    await message.answer("⚠️ Будь ласка, надішліть <b>фото</b> мультиметра.")

@router.message(ReportState.photo_shos, F.photo)
async def set_photo_shos(message: Message, state: FSMContext):
    await state.update_data(photo_shos_id=message.photo[-1].file_id)
    await show_final_confirmation(message, state)

@router.message(ReportState.photo_shos)
async def set_photo_shos_invalid(message: Message, state: FSMContext):
    await message.answer("⚠️ Будь ласка, надішліть <b>фото</b> ШОС (монітора).")

# --- Fallbacks for Inline Keyboard States ---

@router.message(ReportState.selecting_object)
@router.message(ReportState.is_launch_planned)
@router.message(ReportState.planned_work_mode)
@router.message(ReportState.time_type)
@router.message(ReportState.start_time)
@router.message(ReportState.power_type)
@router.message(ReportState.apparatus_check)
@router.message(ReportState.waiting_for_confirmation)
async def handle_inline_kb_fallbacks(message: Message, state: FSMContext):
    # If user clicks a main menu button, we should cancel current report and proceed
    main_commands = ["Графік роботи ГПУ", "Подати чек-лист", "Статус ГПУ", "Адмін панель"]
    if message.text in main_commands:
        await state.clear()
        # Re-route to the appropriate handler based on text
        if message.text == "Адмін панель":
            from app.handlers.admin import cmd_admin_panel
            return await cmd_admin_panel(message, state)
        elif message.text == "Статус ГПУ":
            return await start_short_report(message, state)
        elif message.text == "Подати чек-лист":
            return await start_report(message, state)
        elif message.text == "Графік роботи ГПУ":
            from app.handlers.trader import cmd_trader_schedule_start
            return await cmd_trader_schedule_start(message, state)

    await message.answer("⚠️ Будь ласка, використовуйте <b>кнопки</b> під повідомленням для вибору.")

async def show_final_confirmation(message: Message, state: FSMContext):
    data = await state.get_data()
    is_short = data.get("is_short")
    current_date = datetime.now().strftime("%d.%m.%Y")
    
    # Shorten name for display
    match = re.search(r'\((.*?)\)', data.get('tc_name', ''))
    display_name = match.group(1) if match else data.get('tc_name', '')

    work_mode = data.get('work_mode', '')
    gpu_status = data.get('gpu_status', '')

    if is_short:
        emoji = get_status_emoji(gpu_status, work_mode)
        summary = f"📋 <b>{emoji} Статус ГПУ: {display_name}</b>\n\n"
    else:
        summary = f"📋 <b>ПЕРЕВІРКА ДАНИХ</b>\n\n"
    
    summary += f"<b>Об'єкт:</b> {display_name}\n<b>Дата:</b> {current_date}\n<b>Заповнив:</b> {data.get('full_name')}\n\n"
    
    power_summary = f"{data.get('power_label')} - {data.get('load_power_percent')}% / {data.get('load_power_kw')}кВт"
    if data.get('power_label') == "-":
        power_summary = "-"

    # Determine time label
    time_label = data.get('time_label')
    if is_short:
        if not time_label:
            if data.get('gpu_status') == "Не працює":
                time_label = "2. Час зупинки"
            else:
                time_label = "2. Час запуску"
        
        if not time_label.startswith("2."):
            time_label = f"2. {time_label}"
    else:
        # For full checklist, always use 'Час запуску' (matches old version logic)
        time_label = "2. Час запуску"

    # Logic for point 1 and 4 in short report
    work_mode = data.get('work_mode')
    gpu_status = data.get('gpu_status')
    
    display_work_mode = work_mode
    display_gpu_status = gpu_status

    if is_short:
        if "не готова" in work_mode or "готова до пуску" in work_mode:
            display_work_mode = "—"
            display_gpu_status = work_mode

    fields = [
        ("1. Режим роботи", display_work_mode),
        (time_label, data.get('start_time')),
        ("3. Потужність", power_summary),
        ("4. Статус роботи", display_gpu_status)
    ]
    
    if not is_short:
        fields += [
            ("5. Напруга АКБ", data.get('battery_voltage')),
            ("6. Тиск до пуску ГПУ (GK, до насоса)", f"{data.get('pressure_before')} бар"),
            ("7. Тиск після пуску ГПУ (GK, до насоса)", f"{data.get('pressure_after')} бар"),
            ("8. Вироблено", f"{data.get('total_mwh')} МВт*год"),
            ("9. Відпрацьовано", f"{data.get('total_hours')} м/год"),
            ("10. До відбору оливи", f"{data.get('oil_sampling_limit')} м/год"),
            ("11. Звірка апаратів", "Підтверджено")
        ]

    for label, val in fields:
        summary += f"<b>{label}:</b> {val}\n"

    summary += "\nЯкщо все вірно, натисніть 'Підтвердити'."
    await state.set_state(ReportState.waiting_for_confirmation)
    await message.answer(summary, reply_markup=get_report_confirm_kb())

@router.callback_query(ReportState.waiting_for_confirmation, F.data == "confirm_report")
async def process_report_confirmation(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()
    user_id = callback.from_user.id
    user_data = await get_user(user_id)
    is_admin = user_id in config.admin_ids
    role = user_data['role'] if user_data else 'user'
    is_short = data.get("is_short", False)
    current_date = datetime.now().strftime("%d.%m.%Y")

    # DB & Google Sheets
    await add_report(data)
    
    # Notify API clients via WebSocket
    try:
        from app.api.ws import notify_new_report
        asyncio.create_task(notify_new_report(data))
        
        # --- Web Push Alerts ---
        status = (data.get("gpu_status") or "").lower()
        if "аварії" in status or "не готова" in status or "аваріями" in status:
            from app.api.notifications import broadcast_alert
            alert_msg = f"⚠️ ОБ'ЄКТ: {data.get('tc_name')}\nСТАТУС: {data.get('gpu_status')}"
            asyncio.create_task(broadcast_alert(alert_msg, title="УВАГА: АВАРІЯ ГПУ!"))
        # ----------------------
    except Exception as e:
        logging.error(f"❌ Error notifying API clients/push: {e}")

    if not is_short:
        asyncio.create_task(asyncio.to_thread(export_to_google, data))

    # Local group check
    obj_details = await get_object_by_id(data.get('obj_id'))
    linked_group_id = obj_details.get('telegram_group_id') if obj_details else None

    # Shorten name for display
    match = re.search(r'\((.*?)\)', data.get('tc_name', ''))
    display_name = match.group(1) if match else data.get('tc_name', '')

    # Prepare Group Summary
    work_mode = data.get('work_mode', '')
    gpu_status = data.get('gpu_status', '')
    
    if is_short:
        emoji = get_status_emoji(gpu_status, work_mode)
        group_summary = f"{emoji} <b>Статус ГПУ: {display_name}</b>\n\n"
    else:
        group_summary = f"✅ <b>Звіт по ГПУ</b>\n\n"
    
    group_summary += f"<b>Об'єкт:</b> {display_name}\n<b>Дата:</b> {current_date}\n<b>Заповнив:</b> {data.get('full_name')}\n"
    
    if is_short:
        # For short report, we show points 1-4
        power_summary = f"{data.get('power_label')} - {data.get('load_power_percent')}% / {data.get('load_power_kw')}кВт"
        if data.get('power_label') == "-":
            power_summary = "-"
            
        time_label = data.get('time_label')
        if not time_label:
            if data.get('gpu_status') == "Не працює":
                time_label = "2. Час зупинки"
            else:
                time_label = "2. Час запуску"
        
        if not time_label.startswith("2."):
            time_label = f"2. {time_label}"

        # Logic for point 1 and 4 in short report
        work_mode = data.get('work_mode')
        gpu_status = data.get('gpu_status')
        
        display_work_mode = work_mode
        display_gpu_status = gpu_status
        
        if "не готова" in work_mode or "готова до пуску" in work_mode:
            display_work_mode = "—"
            display_gpu_status = work_mode

        group_summary += (
            f"\n<b>1. Режим роботи:</b> {display_work_mode}\n"
            f"<b>{time_label}:</b> {data.get('start_time')}\n"
            f"<b>3. Потужність:</b> {power_summary}\n"
            f"<b>4. Статус роботи:</b> {display_gpu_status}"
        )
    else:
        # Determine Status Display for point 8
        work_mode = data.get('work_mode')
        gpu_status = data.get('gpu_status')
        
        if work_mode in ["Острів", "Мережа"]:
            status_display = gpu_status
        else:
            if gpu_status == "З аваріями":
                status_display = f'{work_mode} "З аваріями"'
            else:
                status_display = work_mode

        # For full report, we show points 1-7 (original 5-11, as 1-4 are excluded per request)
        group_summary += (
            f"\n<b>1. Напруга АКБ:</b> {data.get('battery_voltage')}\n"
            f"<b>2. Тиск антифризу до пуску ГПУ (GK, до насоса):</b> {data.get('pressure_before')} бар\n"
            f"<b>3. Тиск антифризу після пуску ГПУ (GK, до насоса):</b> {data.get('pressure_after')} бар\n"
            f"<b>4. Всього вироблено:</b> {data.get('total_mwh')} МВт*год\n"
            f"<b>5. Всього відпрацьовано:</b> {data.get('total_hours')} м/год\n"
            f"<b>6. До відбору оливи:</b> {data.get('oil_sampling_limit')} м/год\n"
            f"<b>7. Звірка апаратів:</b> Підтверджено\n"
            f"<b>8. Статус роботи:</b> {status_display}"
        )

    async def deliver(chat_id, custom_text=None):
        text_to_send = custom_text or group_summary
        try:
            if not is_short:
                media = [
                    InputMediaPhoto(media=data['photo_multimeter_id'], caption=text_to_send),
                    InputMediaPhoto(media=data['photo_shos_id'])
                ]
                await bot.send_media_group(chat_id=chat_id, media=media)
            else:
                await bot.send_message(chat_id=chat_id, text=text_to_send)
        except Exception: pass

    await deliver(config.group_id)
    if linked_group_id: await deliver(linked_group_id)
    
    if is_short and config.special_group_id:
        # Remove "Заповнив:" line for special group
        special_summary = "\n".join([line for line in group_summary.split("\n") if "Заповнив:" not in line])
        await deliver(config.special_group_id, custom_text=special_summary)

    await callback.message.edit_text("✅ Звіт успішно збережено!")
    await callback.message.answer("Ви в головному меню.", reply_markup=get_main_menu_keyboard(is_admin=is_admin, role=role))
    await callback.answer()

