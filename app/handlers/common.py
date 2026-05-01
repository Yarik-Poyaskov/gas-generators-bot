import re
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from app.filters.is_admin import IsAdmin
from app.config import config
from app.db.database import get_user, get_user_by_phone, update_user_link
from app.keyboards.reply import get_main_menu_keyboard 
from app.handlers.report import start_report 
from app.states.monthly_report import MonthlyReportState

router = Router()
cancel_router = Router() # Special router for high-priority cancel commands

class RegistrationState(StatesGroup):
    waiting_for_contact = State()

def normalize_phone(phone: str) -> str:
    """Normalizes phone number to international format (380...)."""
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 10 and digits.startswith('0'):
        return '38' + digits
    return digits

# --- Global Cancel Handler ---
# This handler intercepts 'Відміна' or main menu buttons to cancel any process
@cancel_router.message(lambda m: m.text and (m.text.casefold() == "відміна" or m.text in [
    "Графік роботи ГПУ", "Подати чек-лист", "Статус ГПУ", 
    "Адмін панель", "👤 Керування змінами", "📊Звіт показників роботи ГПУ за місяць"
]))
@cancel_router.message(Command("cancel"))
async def global_cancel(message: Message, state: FSMContext):
    """
    Глобальний обробник скасування будь-якої дії.
    Спрацьовує ТІЛЬКИ на ключові слова або кнопки меню.
    """
    user_id = message.from_user.id
    is_admin = user_id in config.admin_ids
    user_data = await get_user(user_id)
    role = user_data['role'] if user_data else 'user'
    
    # If it was a main menu button, we want to clear state and redirect
    if message.text in [
        "Графік роботи ГПУ", "Подати чек-лист", "Статус ГПУ", 
        "Адмін панель", "👤 Керування змінами", "📊Звіт показників роботи ГПУ за місяць"
    ]:
        await state.clear()
        if message.text == "Адмін панель":
            from app.handlers.admin import cmd_admin_panel
            return await cmd_admin_panel(message, state)
        elif message.text == "Статус ГПУ":
            from app.handlers.report import start_short_report
            return await start_short_report(message, state)
        elif message.text == "Подати чек-лист":
            return await start_report(message, state)
        elif message.text == "📊Звіт показників роботи ГПУ за місяць":
            from app.handlers.monthly_report import cmd_monthly_report_start
            return await cmd_monthly_report_start(message, state)
        elif message.text == "Графік роботи ГПУ":
            from app.handlers.trader import cmd_trader_schedule_start
            return await cmd_trader_schedule_start(message, state)
        elif message.text == "👤 Керування змінами":
            from app.handlers.shifts import cmd_shifts_start
            return await cmd_shifts_start(message, state)

    # If it was just 'Відміна' text or /cancel
    await state.clear()
    await message.answer(
        "Дію скасовано. Ви повернулись до головного меню.",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin, role=role)
    )

# Команда для удаления меню в группах
@router.message(Command("clear"))
async def cmd_clear_menu(message: Message):
    await message.answer(
        "Меню видалено для цього чату.",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(Command("start"), F.chat.type == "private")
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    is_admin = user_id in config.admin_ids
    user_data = await get_user(user_id)

    if not user_data and not is_admin:
        await cmd_reset(message, state)
        return

    role = user_data['role'] if user_data else 'user'
    full_name = user_data['full_name'] if user_data else message.from_user.full_name
    
    if role == 'trader':
        msg = f"Вітаю, {full_name}! Тут ви можете подати графік роботи ГПУ."
    else:
        msg = f"Вітаю, {full_name}! Я допоможу вам зібрати щоденний звіт по ГПУ."
    
    await message.answer(
        msg,
        reply_markup=get_main_menu_keyboard(is_admin=is_admin, role=role)
    )

@router.message(Command("reset"), F.chat.type == "private")
async def cmd_reset(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(RegistrationState.waiting_for_contact)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Поділитися контактом", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "Привіт! Щоб я міг працювати, мені потрібно знати ваш номер телефону. "
        "Будь ласка, поділіться своїм контактом, натиснувши кнопку нижче.",
        reply_markup=keyboard
    )

@router.message(RegistrationState.waiting_for_contact, F.contact, F.chat.type == "private")
async def handle_contact(message: Message, state: FSMContext):
    if message.contact and message.contact.user_id == message.from_user.id:
        user_id = message.from_user.id
        phone_number = normalize_phone(message.contact.phone_number)
        username = message.from_user.username
        is_admin = user_id in config.admin_ids

        db_user = await get_user_by_phone(phone_number)
        
        if db_user or is_admin:
            if db_user:
                await update_user_link(phone_number, user_id, username)
                full_name = db_user['full_name']
                role = db_user['role']
            else:
                full_name = f"{message.contact.first_name} {message.contact.last_name or ''}".strip()
                role = 'user'
            
            await state.clear()
            if role == 'trader':
                msg = f"Дякую, {full_name}! Ваші дані підтверджено. Тут ви можете подати графік роботи ГПУ."
            else:
                msg = f"Дякую, {full_name}! Ваші дані підтверджено. Я допоможу вам зібрати щоденний звіт по ГПУ."
                
            await message.answer(
                msg,
                reply_markup=get_main_menu_keyboard(is_admin=is_admin, role=role)
            )
        else:
            await message.answer(
                "Доступ заборонено. Ваш номер телефону не зареєстрований в системі. Зверніться до администратора.",
                reply_markup=ReplyKeyboardRemove()
            )
    else:
        await message.answer(
            "Будь ласка, поділіться своїм власним контактом, натиснувши кнопку.",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(RegistrationState.waiting_for_contact)

@router.message(F.text == "Додому", F.chat.type == "private")
async def cmd_home(message: Message, state: FSMContext):
    user_id = message.from_user.id
    is_admin = user_id in config.admin_ids
    user_data = await get_user(user_id)
    role = user_data['role'] if user_data else 'user'
    await state.clear()
    await message.answer(
        "Ви повернулись до головного меню.",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin, role=role)
    )

@router.message(F.text == "Заповнити Чек-Лист", F.chat.type == "private")
async def cmd_fill_checklist_from_menu(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await get_user(user_id)
    is_admin = user_id in config.admin_ids

    if user_data or is_admin:
        await start_report(message, state)
    else:
        await message.answer(
            "Доступ заборонено. Зверніться до адміністратора.",
            reply_markup=ReplyKeyboardRemove()
        )

@router.message(F.chat.type == "private")
async def echo_unhandled(message: Message, state: FSMContext):
    user_id = message.from_user.id
    is_admin = user_id in config.admin_ids
    user_data = await get_user(user_id)

    if not user_data and not is_admin:
        await message.answer("Доступ заборонено. Зверніться до адміністратора.")
        return

    current_state = await state.get_state()
    if not current_state:
        await message.answer(
            "Ви в головному меню. Виберіть дію:",
            reply_markup=get_main_menu_keyboard(is_admin=is_admin)
        )
