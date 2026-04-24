import json
import re
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta

from app.config import config
from app.db.database import (
    get_user, get_all_objects, get_object_by_id, 
    add_trader_schedule, get_object_users, get_setting
)
from app.keyboards.inline import (
    get_object_selection_kb, get_trader_date_kb, get_trader_hour_kb,
    get_power_percent_kb, get_work_mode_trader_kb, get_next_interval_kb,
    get_report_confirm_kb, get_trader_action_kb, get_schedule_confirm_kb
)
from app.keyboards.reply import get_main_menu_keyboard
from app.states.trader import TraderScheduleState

router = Router()

@router.message(F.text == "Графік роботи ГПУ")
async def cmd_trader_schedule_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await get_user(user_id)
    is_admin = user_id in config.admin_ids
    
    if not is_admin and (not user_data or user_data['role'] != 'trader'):
        return

    await state.clear()
    objects = await get_all_objects()
    await state.set_state(TraderScheduleState.selecting_object)
    await message.answer(
        "Оберіть об'єкт для подачі графіка:",
        reply_markup=get_object_selection_kb(objects, 0, config.users_per_page)
    )

@router.callback_query(TraderScheduleState.selecting_object, F.data.startswith("sel_obj_page:"))
async def process_trader_obj_pagination(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[1])
    objects = await get_all_objects()
    await callback.message.edit_reply_markup(
        reply_markup=get_object_selection_kb(objects, page, config.users_per_page)
    )
    await callback.answer()

@router.callback_query(TraderScheduleState.selecting_object, F.data.startswith("select_obj:"))
async def process_object_selection(callback: CallbackQuery, state: FSMContext):
    obj_id = int(callback.data.split(":")[1])
    obj = await get_object_by_id(obj_id)
    await state.update_data(obj_id=obj_id, tc_name=obj['name'], intervals=[])
    await state.set_state(TraderScheduleState.selecting_date)
    await callback.message.edit_text(f"Об'єкт: <b>{obj['name']}</b>\nОберіть дату:", reply_markup=get_trader_date_kb())
    await callback.answer()

@router.callback_query(TraderScheduleState.selecting_date, F.data.startswith("trader_date:"))
async def process_date_selection(callback: CallbackQuery, state: FSMContext):
    date_type = callback.data.split(":")[1]
    now = datetime.now()
    if date_type == "today":
        target_date_obj = now
    elif date_type == "tomorrow":
        target_date_obj = now + timedelta(days=1)
    else:
        target_date_obj = now + timedelta(days=2)

    target_date_display = target_date_obj.strftime("%d.%m.%Y")
    target_date_db = target_date_obj.strftime("%Y-%m-%d")

    await state.update_data(target_date=target_date_display, target_date_db=target_date_db)
    await state.set_state(TraderScheduleState.selecting_action)
    await callback.message.edit_text(f"Дата: <b>{target_date_display}</b>\nОберіть дію:", reply_markup=get_trader_action_kb())
    await callback.answer()

@router.callback_query(TraderScheduleState.selecting_action, F.data.startswith("trader_action:"))
async def process_trader_action(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[1]

    if action == "not_working":
        await state.update_data(is_not_working=True)
        await show_confirmation(callback, state)
    else:
        await state.update_data(is_not_working=False)
        await state.set_state(TraderScheduleState.selecting_start_hour)
        await callback.message.edit_text("Оберіть годину ПОЧАТКУ інтервалу:", reply_markup=get_trader_hour_kb("Початок", "start_h"))
    await callback.answer()

@router.callback_query(TraderScheduleState.selecting_start_hour, F.data.startswith("start_h:"))
async def process_start_hour(callback: CallbackQuery, state: FSMContext):
    hour = int(callback.data.split(":")[1])
    await state.update_data(current_start_h=hour)
    await state.set_state(TraderScheduleState.selecting_start_minute)
    from app.keyboards.inline import get_trader_minute_kb
    await callback.message.edit_text(f"Початок: {hour:02d}:??\nОберіть хвилини ПОЧАТКУ:", reply_markup=get_trader_minute_kb(hour, "start_m"))
    await callback.answer()

@router.callback_query(TraderScheduleState.selecting_start_minute, F.data.startswith("start_m:"))
async def process_start_minute(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    hour, minute = parts[1], parts[2]
    time_str = f"{hour}:{minute}"
    await state.update_data(current_start=time_str)
    await state.set_state(TraderScheduleState.selecting_end_hour)
    await callback.message.edit_text(f"Початок: {time_str}\nОберіть годину КІНЦЯ інтервалу:", reply_markup=get_trader_hour_kb("Кінець", "end_h"))
    await callback.answer()

@router.callback_query(TraderScheduleState.selecting_end_hour, F.data.startswith("end_h:"))
async def process_end_hour(callback: CallbackQuery, state: FSMContext):
    hour = int(callback.data.split(":")[1])
    await state.update_data(current_end_h=hour)
    await state.set_state(TraderScheduleState.selecting_end_minute)
    from app.keyboards.inline import get_trader_minute_kb
    await callback.message.edit_text(f"Кінець: {hour:02d}:??\nОберіть хвилини КІНЦЯ:", reply_markup=get_trader_minute_kb(hour, "end_m"))
    await callback.answer()

@router.callback_query(TraderScheduleState.selecting_end_minute, F.data.startswith("end_m:"))
async def process_end_minute(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    hour, minute = parts[1], parts[2]
    time_str = f"{hour}:{minute}"
    await state.update_data(current_end=time_str)
    await state.set_state(TraderScheduleState.selecting_power)
    await callback.message.edit_text(f"Кінець: {time_str}\nОберіть значення потужності в %:", reply_markup=get_power_percent_kb())
    await callback.answer()

@router.callback_query(TraderScheduleState.selecting_power, F.data.startswith("trader_power:"))
async def process_power(callback: CallbackQuery, state: FSMContext):
    power = callback.data.split(":")[1]
    power_display = f"{power}%" if power != "skip" else "Н/З"
    await state.update_data(current_power=power_display)
    await state.set_state(TraderScheduleState.selecting_mode)
    await callback.message.edit_text("Оберіть режим роботи:", reply_markup=get_work_mode_trader_kb())
    await callback.answer()

@router.callback_query(TraderScheduleState.selecting_mode, F.data.startswith("trader_mode:"))
async def process_mode(callback: CallbackQuery, state: FSMContext):
    mode = callback.data.split(":")[1]
    mode_display = mode if mode != "skip" else "Н/З"

    data = await state.get_data()
    interval = {
        "start": data['current_start'],
        "end": data['current_end'],
        "power": data['current_power'],
        "mode": mode_display
    }

    intervals = data.get('intervals', [])
    intervals.append(interval)
    await state.update_data(intervals=intervals)

    await state.set_state(TraderScheduleState.asking_next_interval)
    await callback.message.edit_text("Інтервал додано. Бажаєте додати ще один?", reply_markup=get_next_interval_kb())
    await callback.answer()

@router.callback_query(TraderScheduleState.asking_next_interval, F.data == "trader_next:add")
async def process_add_more(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TraderScheduleState.selecting_start_hour)
    await callback.message.edit_text("Оберіть годину ПОЧАТКУ наступного інтервалу:", reply_markup=get_trader_hour_kb("Початок", "start_h"))
    await callback.answer()

@router.callback_query(TraderScheduleState.asking_next_interval, F.data == "trader_next:finish")
async def process_finish(callback: CallbackQuery, state: FSMContext):
    await show_confirmation(callback, state)
    await callback.answer()

async def show_confirmation(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    full_tc_name = data.get('tc_name', '')
    target_date = data.get('target_date', datetime.now().strftime("%d.%m.%Y"))
    is_not_working = data.get('is_not_working', False)

    match_name = re.search(r'\((.*?)\)', full_tc_name)
    display_tc_name = match_name.group(1) if match_name else full_tc_name

    summary = f"📋 <b>ПІДТВЕРДЖЕННЯ ГРАФІКА</b>\n\n"
    summary += f"<b>Об'єкт:</b> {display_tc_name}\n"
    summary += f"<b>Дата:</b> {target_date}\n\n"

    if is_not_working:
        summary += "<b>Статус:</b> НЕ ПРАЦЮЄ"
    else:
        summary += "<b>Інтервали роботи:</b>\n"
        for i, inv in enumerate(data.get('intervals', []), 1):
            summary += f"{i}. {inv['start']} - {inv['end']} | {inv['power']} | {inv['mode']}\n"

    summary += "\nБудь ласка, перевірте дані. Якщо все вірно, натисніть 'Підтвердити'."

    await state.set_state(TraderScheduleState.waiting_for_confirmation)
    await callback.message.edit_text(summary, reply_markup=get_report_confirm_kb())

@router.callback_query(TraderScheduleState.waiting_for_confirmation, F.data == "confirm_report")
async def process_confirm_schedule(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    obj_id = data.get('obj_id')
    full_tc_name = data.get('tc_name', '')
    target_date_display = data.get('target_date')
    target_date_db = data.get('target_date_db')
    is_not_working = data.get('is_not_working', False)
    intervals = data.get('intervals', [])

    match_name = re.search(r'\((.*?)\)', full_tc_name)
    display_tc_name = match_name.group(1) if match_name else full_tc_name

    # 1. Save to DB using YYYY-MM-DD
    schedule_id = await add_trader_schedule(
        object_id=obj_id,
        trader_id=callback.from_user.id,
        target_date=target_date_db,
        schedule_data=json.dumps(intervals, ensure_ascii=False),
        is_not_working=is_not_working
    )

    # 1.1 Fetch object details
    obj_details = await get_object_by_id(obj_id)
    linked_group_id = obj_details.get('telegram_group_id')

    # Get user role for correct keyboard
    user_id = callback.from_user.id
    user_data = await get_user(user_id)
    is_admin = user_id in config.admin_ids
    role = user_data['role'] if user_data else 'trader'

    await state.clear()
    await callback.message.edit_text("✅ Графік успішно збережено та надано для підтвердження!")
    await callback.message.answer("Повернуто до головного меню.", reply_markup=get_main_menu_keyboard(is_admin=is_admin, role=role))

    # 2. Form message for users
    msg_text = f"📢 <b>ГРАФІК РОБОТИ ГПУ</b>\n\n"
    msg_text += f"<b>Об'єкт:</b> {display_tc_name}\n"
    msg_text += f"<b>Дата:</b> {target_date_display}\n\n"

    if is_not_working:
        msg_text += "<b>Статус:</b> НЕ ПРАЦЮЄ"
    else:
        msg_text += "<b>Інтервали:</b>\n"
        for i, inv in enumerate(intervals, 1):
            msg_text += f"{i}. {inv['start']} - {inv['end']} | {inv['power']} | {inv['mode']}\n"

    msg_text += "\nБудь ласка, ознайомтесь та підтвердіть отримання графіка."

    # 3. Find and notify users
    users = await get_object_users(obj_id)
    confirm_kb = get_schedule_confirm_kb(schedule_id)

    # Get settings
    notify_pm = await get_setting("notify_trader_pm", "1") == "1"
    notify_groups = await get_setting("notify_trader_groups", "1") == "1"

    # Notify Linked Group
    if linked_group_id and notify_groups:
        try:
            await bot.send_message(chat_id=linked_group_id, text=msg_text, reply_markup=confirm_kb)
        except Exception as e:
            print(f"Error notifying group {linked_group_id}: {e}")

    # Notify Test Special Group (always, if set)
    if config.test_special_group_id:
        try:
            await bot.send_message(chat_id=config.test_special_group_id, text=msg_text, reply_markup=confirm_kb)
        except Exception as e:
            print(f"Error notifying test group: {e}")

    # Notify Users PM
    if notify_pm:
        for user in users:
            if user['user_id']:
                try:
                    await bot.send_message(chat_id=user['user_id'], text=msg_text, reply_markup=confirm_kb)
                except Exception as e:
                    print(f"Error notifying user {user['full_name']}: {e}")

    await callback.answer()

# --- Fallbacks ---

@router.message(TraderScheduleState.selecting_object)
@router.message(TraderScheduleState.selecting_date)
@router.message(TraderScheduleState.selecting_action)
@router.message(TraderScheduleState.selecting_start_hour)
@router.message(TraderScheduleState.selecting_start_minute)
@router.message(TraderScheduleState.selecting_end_hour)
@router.message(TraderScheduleState.selecting_end_minute)
@router.message(TraderScheduleState.selecting_power)
@router.message(TraderScheduleState.selecting_mode)
@router.message(TraderScheduleState.asking_next_interval)
@router.message(TraderScheduleState.waiting_for_confirmation)
async def handle_trader_inline_kb_fallbacks(message: Message, state: FSMContext):
    # If user clicks a main menu button, we should cancel current process and proceed
    main_commands = ["Графік роботи ГПУ", "Подати чек-лист", "Статус ГПУ", "Адмін панель", "Відміна"]
    
    if message.text in main_commands:
        await state.clear()
        if message.text == "Адмін панель":
            from app.handlers.admin import cmd_admin_panel
            return await cmd_admin_panel(message, state)
        elif message.text == "Статус ГПУ":
            from app.handlers.report import start_short_report
            return await start_short_report(message, state)
        elif message.text == "Подати чек-лист":
            from app.handlers.report import start_report_button
            return await start_report_button(message, state)
        elif message.text == "Графік роботи ГПУ":
            return await cmd_trader_schedule_start(message, state)
        elif message.text == "Відміна":
            from app.handlers.report import cmd_cancel_report
            return await cmd_cancel_report(message, state)

    await message.answer("⚠️ Будь ласка, використовуйте <b>кнопки</b> під повідомленням.")
