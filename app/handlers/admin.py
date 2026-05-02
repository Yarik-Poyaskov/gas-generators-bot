import re
from aiogram import Router, F, Bot
from aiogram.types import Message, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.config import config
from app.filters.is_admin import IsAdmin
from app.db.database import (
    add_authorized_user, get_all_users, update_user_name_by_id, 
    delete_user_by_id, update_user_phone, get_user_by_db_id, get_all_traders,
    add_object, get_all_objects, get_object_by_id, update_object_name, delete_object_by_id,
    update_object_required,
    toggle_user_object_link, get_user_objects, get_object_users,
    get_all_telegram_groups, link_group_to_object, get_telegram_group
)
from app.keyboards.reply import (
    get_admin_main_keyboard, get_main_menu_keyboard, get_simple_cancel_kb,
    get_user_list_manage_kb, get_objects_mgmt_keyboard, get_admin_trader_edit_keyboard,
    get_admin_reports_keyboard
)
from app.keyboards.inline import (
    get_users_inline_keyboard, get_objects_inline_keyboard, get_user_objects_setup_kb,
    get_confirmation_kb, get_role_selection_kb, get_traders_inline_keyboard,
    get_object_manage_kb, get_groups_selection_kb
)
from app.states.admin import AdminState

router = Router()
router.message.filter(IsAdmin())

def normalize_phone(phone: str) -> str:
    """Normalizes phone number to international format (380...)."""
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 10 and digits.startswith('0'):
        return '38' + digits
    return digits

@router.message(F.text == "Адмін панель")
async def cmd_admin_panel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Ласкаво просимо до адмін-панелі. Оберіть дію:",
        reply_markup=get_admin_main_keyboard()
    )

@router.message(F.text.in_(["Назад до головного меню", "До головного меню"]))
async def cmd_back_to_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Повертаємось до головного меню.",
        reply_markup=get_main_menu_keyboard(is_admin=True)
    )

@router.message(F.text == "Додати користувача")
async def cmd_add_user_start(message: Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_role)
    await message.answer(
        "Оберіть роль для нового запису:",
        reply_markup=get_role_selection_kb()
    )

@router.callback_query(AdminState.waiting_for_role, F.data.startswith("role:"))
async def process_role_selection(callback: CallbackQuery, state: FSMContext):
    role = callback.data.split(":")[1]
    await state.update_data(new_user_role=role)
    await state.set_state(AdminState.waiting_for_user_phone)
    role_name = "користувача" if role == 'user' else "трейдера"
    await callback.message.edit_text(f"Обрано роль: {role.capitalize()}.")
    await callback.message.answer(
        f"Будь ласка, введіть номер телефону {role_name} (наприклад, 380991234567):",
        reply_markup=get_simple_cancel_kb()
    )
    await callback.answer()

@router.message(AdminState.waiting_for_user_phone)
async def process_user_phone(message: Message, state: FSMContext):
    if message.text == "Відміна":
        await cmd_admin_panel(message, state)
        return

    phone = normalize_phone(message.text)
    if not (10 <= len(phone) <= 15):
        await message.answer("Некоректний формат номера. Спробуйте ще раз (тільки цифри, 10-15 знаків):")
        return

    await state.update_data(new_user_phone=phone)
    await state.set_state(AdminState.waiting_for_user_name)
    data = await state.get_data()
    role_name = "користувача" if data.get('new_user_role') == 'user' else "трейдера"
    await message.answer(f"Тепер введіть повне ім'я {role_name}:")

@router.message(AdminState.waiting_for_user_name)
async def process_user_name(message: Message, state: FSMContext):
    if message.text == "Відміна":
        await cmd_admin_panel(message, state)
        return

    data = await state.get_data()
    phone = data['new_user_phone']
    role = data.get('new_user_role', 'user')
    name = message.text.strip()

    await add_authorized_user(phone, name, role)
    await state.clear()
    role_display = "Користувача" if role == 'user' else "Трейдера"
    await message.answer(
        f"{role_display} {name} (+{phone}) успішно додано!",
        reply_markup=get_admin_main_keyboard()
    )

@router.message(F.text == "Список користувачів")
async def cmd_user_list(message: Message):
    users = await get_all_users()
    if not users:
        await message.answer("Список користувачів порожній.")
        return

    await message.answer(
        "Відкрито список користувачів.",
        reply_markup=get_user_list_manage_kb()
    )

    text = "Оберіть користувача для керування:\n\n⏳ - ще не зайшов у бот\n✅ - активний"
    await message.answer(
        text,
        reply_markup=get_users_inline_keyboard(users, 0, config.users_per_page)
    )

@router.callback_query(F.data.startswith("users_page:"))
async def process_users_pagination(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    users = await get_all_users()
    await callback.message.edit_reply_markup(reply_markup=get_users_inline_keyboard(users, page, config.users_per_page))
    await callback.answer()

@router.message(F.text == "Список трейдерів")
async def cmd_trader_list(message: Message):
    traders = await get_all_traders()
    if not traders:
        await message.answer("Список трейдерів порожній.")
        return

    await message.answer(
        "Відкрито список трейдерів.",
        reply_markup=get_user_list_manage_kb()
    )

    text = "Оберіть трейдера для керування:\n\n⏳ - ще не зайшов у бот\n👤 - активний"
    await message.answer(
        text,
        reply_markup=get_traders_inline_keyboard(traders, 0, config.users_per_page)
    )

@router.callback_query(F.data.startswith("traders_page:"))
async def process_traders_pagination(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    traders = await get_all_traders()
    await callback.message.edit_reply_markup(reply_markup=get_traders_inline_keyboard(traders, page, config.users_per_page))
    await callback.answer()

@router.message(F.text == "📊 Звіти та підсумки")
async def cmd_admin_reports_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Розділ звітів та підсумків. Оберіть дію:",
        reply_markup=get_admin_reports_keyboard()
    )

@router.message(F.text == "Звіт по трейдеру (на сьогодні)")
async def cmd_admin_schedule_status_today(message: Message):
    from datetime import datetime
    from app.db.database import get_schedules_for_report
    
    today_db_str = datetime.now().strftime("%Y-%m-%d")
    today_display_str = datetime.now().strftime("%d.%m.%Y")
    
    schedules = await get_schedules_for_report(today_db_str)
    submitted_schedules = [s for s in schedules if s['schedule_id']]
    
    if not submitted_schedules:
        await message.answer(f"ℹ️ На сьогодні ({today_display_str}) ще не подано жодного графіка.")
        return

    report_text = f"📊 <b>СТАТУС ПОДАНИХ ГРАФІКІВ (НА СЬОГОДНІ)</b>\n"
    report_text += f"📅 Дата графіка: {today_display_str}\n"
    report_text += f"⏰ Час звіту: {datetime.now().strftime('%H:%M')}\n\n"

    for s in submitted_schedules:
        full_tc_name = s.get('tc_name', '')
        match_name = re.search(r'\((.*?)\)', full_tc_name)
        display_tc_name = match_name.group(1) if match_name else full_tc_name
        
        status_icon = "✅" if s['confirmed_by'] else "⏳"
        confirmed_info = f"\n   └ Підтвердив: {s['confirmed_user_name']}" if s['confirmed_by'] else "\n   └ <b>ОЧІКУЄ ПІДТВЕРДЖЕННЯ</b>"
        work_status = "НЕ ПРАЦЮЄ" if s['is_not_working'] else "Є ГРАФІК"
        
        report_text += f"{status_icon} <b>{display_tc_name}</b>: {work_status}{confirmed_info}\n\n"

    await message.answer(report_text, parse_mode="HTML")

@router.message(F.text == "Звіт по трейдеру (на завтра)")
async def cmd_admin_schedule_status_tomorrow(message: Message):
    from datetime import datetime, timedelta
    from app.db.database import get_schedules_for_report
    
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_db_str = tomorrow.strftime("%Y-%m-%d")
    tomorrow_display_str = tomorrow.strftime("%d.%m.%Y")
    
    schedules = await get_schedules_for_report(tomorrow_db_str)
    submitted_schedules = [s for s in schedules if s['schedule_id']]
    
    if not submitted_schedules:
        await message.answer(f"ℹ️ На завтра ({tomorrow_display_str}) ще не подано жодного графіка.")
        return

    report_text = f"📊 <b>СТАТУС ПОДАНИХ ГРАФІКІВ (НА ЗАВТРА)</b>\n"
    report_text += f"📅 Дата графіка: {tomorrow_display_str}\n"
    report_text += f"⏰ Час звіту: {datetime.now().strftime('%H:%M')}\n\n"

    for s in submitted_schedules:
        full_tc_name = s.get('tc_name', '')
        match_name = re.search(r'\((.*?)\)', full_tc_name)
        display_tc_name = match_name.group(1) if match_name else full_tc_name
        
        status_icon = "✅" if s['confirmed_by'] else "⏳"
        confirmed_info = f"\n   └ Підтвердив: {s['confirmed_user_name']}" if s['confirmed_by'] else "\n   └ <b>ОЧІКУЄ ПІДТВЕРДЖЕННЯ</b>"
        work_status = "НЕ ПРАЦЮЄ" if s['is_not_working'] else "Є ГРАФІК"
        
        report_text += f"{status_icon} <b>{display_tc_name}</b>: {work_status}{confirmed_info}\n\n"

    await message.answer(report_text, parse_mode="HTML")

@router.message(F.text == "Звіт по об'єктам (за сьогодні)")
async def cmd_admin_summary_report_today(message: Message, bot: Bot):
    from send_summary_report import run_summary_report
    await message.answer("⏳ Генерується звіт, зачекайте кілька секунд...")
    await run_summary_report(bot, target_chat_id=message.chat.id)

@router.message(F.text == "Керування об'єктами")
async def cmd_objects_mgmt(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Управління об'єктами (ТРЦ/Локації):",
        reply_markup=get_objects_mgmt_keyboard()
    )

@router.message(F.text == "Список об'єктів")
async def cmd_object_list(message: Message):
    objects = await get_all_objects()
    if not objects:
        await message.answer("Список об'єктів порожній.")
        return
    await message.answer("Відкрито список об'єктів.", reply_markup=get_user_list_manage_kb())
    await message.answer("Оберіть об'єкт для керування:", reply_markup=get_objects_inline_keyboard(objects, 0, config.users_per_page))

@router.message(F.text == "Назад до адмін-панелі")
async def cmd_back_to_admin(message: Message, state: FSMContext):
    await cmd_admin_panel(message, state)

# --- Universal Inline Close ---
@router.callback_query(F.data == "close_admin_inline")
async def process_close_admin_inline(callback: CallbackQuery):
    if callback.message:
        try:
            await callback.message.delete()
        except Exception:
            pass
    await callback.answer()

# --- User Edit Actions ---
@router.callback_query(F.data.startswith("manage_user:"))
async def process_manage_user(callback: CallbackQuery, state: FSMContext):
    user_id_db = int(callback.data.split(":")[1])
    await state.update_data(managing_user_id=user_id_db) # Save ID to state!
    user = await get_user_by_db_id(user_id_db)
    if not user:
        await callback.answer("Користувача не знайдено.")
        return

    objs = await get_user_objects(user_id_db)
    objs_list = ", ".join([o['name'] for o in objs]) if objs else "немає"

    text = (
        f"👤 **Керування користувачем**\n\n"
        f"Ім'я: **{user['full_name']}**\n"
        f"Телефон: `+{user['phone_number']}`\n"
        f"Роль: {user['role']}\n"
        f"ID: <code>{user['user_id'] or 'не зайшов'}</code>\n"
        f"Об'єкти: {objs_list}"
    )

    from app.keyboards.reply import get_admin_user_edit_keyboard
    await callback.message.answer(text, reply_markup=get_admin_user_edit_keyboard(), parse_mode="HTML")
    await callback.message.delete()
    await callback.answer()

@router.message(F.text == "Назад до списку користувачів")
async def cmd_back_to_user_list(message: Message, state: FSMContext):
    await state.update_data(managing_user_id=None)
    await cmd_user_list(message)

@router.message(F.text == "Назад до списку трейдерів")
async def cmd_back_to_trader_list(message: Message, state: FSMContext):
    await state.update_data(managing_trader_id=None)
    await cmd_trader_list(message)

@router.message(F.text == "Змінити ім'я користувача")
async def edit_user_name_cmd(message: Message, state: FSMContext):
    data = await state.get_data()
    if 'managing_user_id' not in data:
        await message.answer("Помилка: користувача не обрано.")
        return
    await state.set_state(AdminState.waiting_for_edit_name)
    await message.answer("Введіть нове ім'я для користувача:", reply_markup=get_simple_cancel_kb())

@router.message(AdminState.waiting_for_edit_name)
async def process_edit_user_name_finish(message: Message, state: FSMContext):
    if message.text == "Відміна":
        await state.set_state(None)
        await message.answer("Скасовано.", reply_markup=get_admin_main_keyboard())
        return
    
    data = await state.get_data()
    user_id_db = data['managing_user_id']
    new_name = message.text.strip()
    await update_user_name_by_id(user_id_db, new_name)
    await state.set_state(None)
    await message.answer(f"✅ Ім'я змінено на: {new_name}", reply_markup=get_admin_main_keyboard())

@router.message(F.text == "Змінити номер телефону")
async def edit_user_phone_cmd(message: Message, state: FSMContext):
    data = await state.get_data()
    if 'managing_user_id' not in data:
        await message.answer("Помилка: користувача не обрано.")
        return
    await state.set_state(AdminState.waiting_for_edit_phone)
    await message.answer("Введіть новий номер телефону (380...):", reply_markup=get_simple_cancel_kb())

@router.message(AdminState.waiting_for_edit_phone)
async def process_edit_user_phone_finish(message: Message, state: FSMContext):
    if message.text == "Відміна":
        await state.set_state(None)
        await message.answer("Скасовано.", reply_markup=get_admin_main_keyboard())
        return
    
    phone = normalize_phone(message.text)
    if not (10 <= len(phone) <= 15):
        await message.answer("Некоректний формат.")
        return

    data = await state.get_data()
    user_id_db = data['managing_user_id']
    await update_user_phone(user_id_db, phone)
    await state.set_state(None)
    await message.answer(f"✅ Номер змінено на: +{phone}", reply_markup=get_admin_main_keyboard())

@router.message(F.text == "Керувати об'єктами користувача")
async def manage_user_objects_cmd(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id_db = data.get('managing_user_id')
    if not user_id_db:
        await message.answer("Користувача не обрано.")
        return
    
    user = await get_user_by_db_id(user_id_db)
    all_objs = await get_all_objects()
    user_objs = await get_user_objects(user_id_db)
    
    await message.answer(
        f"Керування об'єктами для <b>{user['full_name']}</b>:",
        reply_markup=get_user_objects_setup_kb(all_objs, user_objs, user_id_db, page=0),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("toggle_uobj:"))
async def process_toggle_user_object(callback: CallbackQuery):
    _, user_db_id, obj_id, page = callback.data.split(":")
    user_db_id, obj_id, page = int(user_db_id), int(obj_id), int(page)
    
    await toggle_user_object_link(user_db_id, obj_id)
    
    all_objs = await get_all_objects()
    user_objs = await get_user_objects(user_db_id)
    
    await callback.message.edit_reply_markup(
        reply_markup=get_user_objects_setup_kb(all_objs, user_objs, user_db_id, page=page)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("uobj_page:"))
async def process_user_objects_pagination(callback: CallbackQuery):
    _, user_db_id, page = callback.data.split(":")
    user_db_id, page = int(user_db_id), int(page)
    
    all_objs = await get_all_objects()
    user_objs = await get_user_objects(user_db_id)
    
    await callback.message.edit_reply_markup(
        reply_markup=get_user_objects_setup_kb(all_objs, user_objs, user_db_id, page=page)
    )
    await callback.answer()

@router.message(F.text == "Видалити користувача")
async def delete_user_cmd(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id_db = data.get('managing_user_id')
    if not user_id_db:
        await message.answer("Користувача не обрано.")
        return
    
    user = await get_user_by_db_id(user_id_db)
    await message.answer(
        f"Ви впевнені, що хочете видалити користувача <b>{user['full_name']}</b>?",
        reply_markup=get_confirmation_kb(f"confirm_del_user:{user_id_db}", "close_admin_inline"),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("confirm_del_user:"))
async def process_delete_user_finish(callback: CallbackQuery, state: FSMContext):
    user_id_db = int(callback.data.split(":")[1])
    await delete_user_by_id(user_id_db)
    await state.update_data(managing_user_id=None)
    await callback.message.edit_text("✅ Користувача видалено.")
    await callback.message.answer("Ви в адмін-панелі.", reply_markup=get_admin_main_keyboard())
    await callback.answer()

# --- Trader Management (Details & Actions) ---
@router.callback_query(F.data.startswith("manage_trader:"))
async def process_manage_trader(callback: CallbackQuery, state: FSMContext):
    trader_id_db = int(callback.data.split(":")[1])
    await state.update_data(managing_trader_id=trader_id_db)
    trader = await get_user_by_db_id(trader_id_db)
    if not trader:
        await callback.answer("Трейдера не знайдено.")
        return

    text = (
        f"👤 **Керування трейдером**\n\n"
        f"Ім'я: **{trader['full_name']}**\n"
        f"Телефон: `+{trader['phone_number']}`\n"
        f"ID: <code>{trader['user_id'] or 'не зайшов'}</code>"
    )

    await callback.message.answer(text, reply_markup=get_admin_trader_edit_keyboard())
    await callback.message.delete()
    await callback.answer()

@router.message(F.text == "Змінити ім'я")
async def edit_trader_name_cmd(message: Message, state: FSMContext):
    data = await state.get_data()
    if 'managing_trader_id' not in data:
        await message.answer("Трейдера не обрано.")
        return
    await state.set_state(AdminState.waiting_for_trader_edit_name)
    await message.answer("Введіть нове ім'я для трейдера:", reply_markup=get_simple_cancel_kb())

@router.message(AdminState.waiting_for_trader_edit_name)
async def process_edit_trader_name_finish(message: Message, state: FSMContext):
    if message.text == "Відміна":
        await state.set_state(None)
        await message.answer("Скасовано.", reply_markup=get_admin_main_keyboard())
        return
    
    data = await state.get_data()
    trader_id_db = data['managing_trader_id']
    new_name = message.text.strip()
    await update_user_name_by_id(trader_id_db, new_name)
    await state.set_state(None)
    await message.answer(f"✅ Ім'я трейдера змінено на: {new_name}", reply_markup=get_admin_main_keyboard())

@router.message(F.text == "Змінити номер")
async def edit_trader_phone_cmd(message: Message, state: FSMContext):
    data = await state.get_data()
    if 'managing_trader_id' not in data:
        await message.answer("Трейдера не обрано.")
        return
    await state.set_state(AdminState.waiting_for_trader_edit_phone)
    await message.answer("Введіть новий телефон трейдера (380...):", reply_markup=get_simple_cancel_kb())

@router.message(AdminState.waiting_for_trader_edit_phone)
async def process_edit_trader_phone_finish(message: Message, state: FSMContext):
    if message.text == "Відміна":
        await state.set_state(None)
        await message.answer("Скасовано.", reply_markup=get_admin_main_keyboard())
        return
    
    phone = normalize_phone(message.text)
    if not (10 <= len(phone) <= 15):
        await message.answer("Некоректний формат.")
        return

    data = await state.get_data()
    trader_id_db = data['managing_trader_id']
    await update_user_phone(trader_id_db, phone)
    await state.set_state(None)
    await message.answer(f"✅ Телефон трейдера змінено на: +{phone}", reply_markup=get_admin_main_keyboard())

@router.message(F.text == "Видалити трейдера")
async def delete_trader_cmd(message: Message, state: FSMContext):
    data = await state.get_data()
    trader_id_db = data.get('managing_trader_id')
    if not trader_id_db:
        await message.answer("Трейдера не обрано.")
        return
    
    trader = await get_user_by_db_id(trader_id_db)
    await message.answer(
        f"Ви впевнені, що хочете видалити трейдера <b>{trader['full_name']}</b>?",
        reply_markup=get_confirmation_kb(f"confirm_del_trader:{trader_id_db}", "close_admin_inline"),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("confirm_del_trader:"))
async def process_delete_trader_finish(callback: CallbackQuery, state: FSMContext):
    trader_id_db = int(callback.data.split(":")[1])
    await delete_user_by_id(trader_id_db)
    await state.update_data(managing_trader_id=None)
    await callback.message.edit_text("✅ Трейдера видалено.")
    await callback.message.answer("Ви в адмін-панелі.", reply_markup=get_admin_main_keyboard())
    await callback.answer()

@router.message(F.text == "Мої об'єкти")
async def cmd_my_objects(message: Message):
    user_id = message.from_user.id
    from app.db.database import get_user_objects_by_tg_id, get_all_objects
    
    user_objs = await get_user_objects_by_tg_id(user_id)
    if not user_objs and user_id in config.admin_ids:
        user_objs = await get_all_objects()
        
    if not user_objs:
        await message.answer("За вами не закріплено жодного об'єкта.")
        return
        
    objs_list = "\n".join([f"— {obj['name']}" for obj in user_objs])
    await message.answer(f"<b>Ваші закріплені об'єкти:</b>\n\n{objs_list}", parse_mode="HTML")

# --- Pagination for Objects ---
@router.callback_query(F.data.startswith("objs_page:"))
async def process_objs_pagination(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    objects = await get_all_objects()
    await callback.message.edit_reply_markup(reply_markup=get_objects_inline_keyboard(objects, page, config.users_per_page))
    await callback.answer()

# --- Object Details & Management ---
@router.callback_query(F.data.startswith("manage_obj:"))
async def process_manage_object(callback: CallbackQuery):
    obj_id = int(callback.data.split(":")[1])
    obj = await get_object_by_id(obj_id)
    if not obj:
        await callback.answer("Об'єкт не знайдено.")
        return

    group_info = "немає"
    if obj['telegram_group_id']:
        group = await get_telegram_group(obj['telegram_group_id'])
        group_info = group['title'] if group else f"ID: {obj['telegram_group_id']}"

    is_req = bool(obj.get('is_required', 1))
    req_text = "✅ ТАК" if is_req else "❌ НІ"

    text = f"🏢 **Керування об'єктом**\n\n"
    text += f"ID: `{obj['id']}`\n"
    text += f"Назва: **{obj['name']}**\n"
    text += f"Група: {group_info}\n"
    text += f"Обов'язковий звіт: {req_text}"

    await callback.message.edit_text(text, reply_markup=get_object_manage_kb(obj['id'], is_req), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("toggle_obj_req:"))
async def process_toggle_obj_required(callback: CallbackQuery):
    parts = callback.data.split(":")
    obj_id = int(parts[1])
    current_val = int(parts[2])
    
    new_val = not bool(current_val)
    await update_object_required(obj_id, new_val)
    
    await callback.answer(f"✅ Статус обов'язковості змінено на {'ТАК' if new_val else 'НІ'}")
    await process_manage_object(callback)

# --- Rename Object ---
@router.callback_query(F.data.startswith("edit_obj_name:"))
async def process_rename_obj_start(callback: CallbackQuery, state: FSMContext):
    obj_id = int(callback.data.split(":")[1])
    await state.update_data(edit_obj_id=obj_id)
    await state.set_state(AdminState.waiting_for_edit_object_name)
    await callback.message.answer("Введіть нову назву для об'єкта:", reply_markup=get_simple_cancel_kb())
    await callback.answer()

@router.message(AdminState.waiting_for_edit_object_name)
async def process_rename_obj_finish(message: Message, state: FSMContext):
    if message.text == "Відміна":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=get_admin_main_keyboard())
        return

    data = await state.get_data()
    obj_id = data['edit_obj_id']
    new_name = message.text.strip()
    
    await update_object_name(obj_id, new_name)
    await state.clear()
    await message.answer(f"✅ Назву об'єкта змінено на: **{new_name}**", parse_mode="Markdown", reply_markup=get_admin_main_keyboard())

# --- Link Group ---
@router.callback_query(F.data.startswith("link_obj_grp:"))
async def process_link_grp_start(callback: CallbackQuery):
    obj_id = int(callback.data.split(":")[1])
    groups = await get_all_telegram_groups()
    
    if not groups:
        await callback.answer("⚠️ Немає зареєстрованих груп. Використайте /init у групі.", show_alert=True)
        return

    await callback.message.edit_text(
        "Оберіть групу для прив'язки до об'єкта:",
        reply_markup=get_groups_selection_kb(groups, obj_id)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("link_grp:"))
async def process_link_grp_finish(callback: CallbackQuery):
    parts = callback.data.split(":")
    obj_id = int(parts[1])
    group_id = parts[2]

    # "none" means unlink
    final_group_id = None if group_id == "none" else int(group_id)
    await link_group_to_object(obj_id, final_group_id)

    await callback.answer("✅ Налаштування групи оновлено!")
    # Show object details again
    await process_manage_object(callback)

@router.message(F.text == "Додати об'єкт")
async def cmd_add_object_start(message: Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_object_name)
    await message.answer("Введіть назву для нового об'єкта:", reply_markup=get_simple_cancel_kb())

@router.message(AdminState.waiting_for_object_name)
async def process_add_object_name(message: Message, state: FSMContext):
    if message.text == "Відміна":
        await cmd_objects_mgmt(message, state)
        return

    name = message.text.strip()
    await add_object(name)
    await state.clear()
    await message.answer(f"✅ Об'єкт **{name}** успішно додано!", parse_mode="Markdown", reply_markup=get_objects_mgmt_keyboard())

# --- Delete Object ---
@router.callback_query(F.data.startswith("delete_obj:"))
async def process_delete_obj_start(callback: CallbackQuery):
    obj_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "⚠️ **Ви впевнені, що хочете видалити цей об'єкт?**\nЦе видалить всі зв'язки з користувачами, але звіти залишаться в базі.",
        reply_markup=get_confirmation_kb(f"confirm_del_obj:{obj_id}", "objs_page:0"),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_del_obj:"))
async def process_delete_obj_finish(callback: CallbackQuery):
    obj_id = int(callback.data.split(":")[1])
    await delete_object_by_id(obj_id)
    await callback.answer("✅ Об'єкт видалено.")
    # Return to objects list
    objects = await get_all_objects()
    await callback.message.edit_text("Оберіть об'єкт для керування:", reply_markup=get_objects_inline_keyboard(objects, 0, config.users_per_page))

# --- Show Object Users ---
@router.callback_query(F.data.startswith("show_obj_users:"))
async def process_show_obj_users(callback: CallbackQuery):
    obj_id = int(callback.data.split(":")[1])
    users = await get_object_users(obj_id)
    
    if not users:
        await callback.answer("За цим об'єктом не закріплено жодного користувача.", show_alert=True)
        return
        
    user_list = "\n".join([f"— {u['full_name']} (+{u['phone_number']})" for u in users])
    await callback.message.answer(f"👥 **Користувачі об'єкта:**\n\n{user_list}", parse_mode="Markdown")
    await callback.answer()
