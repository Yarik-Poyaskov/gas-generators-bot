import re
import logging
from datetime import datetime, timedelta
from aiogram import Router, F, Bot, html
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from app.db.database import (
    get_user, get_user_objects_by_tg_id, get_all_objects, 
    get_object_by_id, add_monthly_report
)
from app.keyboards.reply import (
    get_main_menu_keyboard, get_simple_cancel_kb, get_cancel_keyboard
)
from app.keyboards.inline import (
    get_monthly_objects_kb, get_confirmation_kb
)
from app.states.monthly_report import MonthlyReportState
from app.config import config

router = Router()

def get_report_period_uk():
    """Returns (month_name, year) for the PREVIOUS month."""
    now = datetime.now()
    # Go back to the last day of previous month
    first_day_this_month = now.replace(day=1)
    last_day_prev_month = first_day_this_month - timedelta(days=1)
    
    months = {
        1: "Січень", 2: "Лютий", 3: "Березень", 4: "Квітень",
        5: "Травень", 6: "Червень", 7: "Липень", 8: "Серпень",
        9: "Вересень", 10: "Жовтень", 11: "Листопад", 12: "Грудень"
    }
    
    month_name = months[last_day_prev_month.month]
    year = last_day_prev_month.year
    return month_name, year

@router.message(F.text.in_([
    "📊Звіт показників роботи ГПУ за місяць(різниця показників газу)",
    "📊Звіт показників роботи ГПУ за місяць(показники газового коректора)"
]))
async def cmd_monthly_report_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await get_user(user_id)
    is_admin = user_id in config.admin_ids

    if not user_data and not is_admin:
        await message.answer("Доступ заборонено.")
        return

    # Clear state and start
    await state.clear()
    
    # Save report type
    report_type = "difference" if "різниця" in message.text else "corrector"
    await state.update_data(report_type=report_type)
    
    # Get user objects
    user_objs = await get_user_objects_by_tg_id(user_id)
    if not user_objs and is_admin:
        user_objs = await get_all_objects()

    if not user_objs:
        await message.answer("За вами не закріплено жодного об'єкта.")
        return

    month_name, year = get_report_period_uk()

    if len(user_objs) == 1:
        obj = user_objs[0]
        await state.update_data(object_id=obj['id'], tc_name=obj['name'])
        await state.set_state(MonthlyReportState.energy_mwh)
        await message.answer(
            f"📊 <b>Місячний звіт: {html.quote(obj['name'])}</b>\n"
            f"Період: {month_name} {year}\n\n"
            f"1️⃣ Введіть кількість згенерованої енергії за місяць (МВт*год):",
            reply_markup=get_simple_cancel_kb(),
            parse_mode="HTML"
        )
    else:
        await state.set_state(MonthlyReportState.selecting_object)
        await message.answer(
            "Оберіть об'єкт для місячного звіту:",
            reply_markup=get_monthly_objects_kb(user_objs, 0, 10)
        )

@router.callback_query(MonthlyReportState.selecting_object, F.data.startswith("monthly_objs_page:"))
async def handle_monthly_objs_pagination(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    is_admin = user_id in config.admin_ids
    
    user_objs = await get_user_objects_by_tg_id(user_id)
    if not user_objs and is_admin:
        user_objs = await get_all_objects()
        
    await callback.message.edit_reply_markup(
        reply_markup=get_monthly_objects_kb(user_objs, page, 10)
    )
    await callback.answer()

@router.callback_query(MonthlyReportState.selecting_object, F.data.startswith("monthly_obj:"))
async def handle_object_selection(callback: CallbackQuery, state: FSMContext):
    obj_id = int(callback.data.split(":")[1])
    obj = await get_object_by_id(obj_id)
    
    await state.update_data(object_id=obj_id, tc_name=obj['name'])
    await state.set_state(MonthlyReportState.energy_mwh)
    
    month_name, year = get_report_period_uk()
    
    await callback.message.edit_text(
        f"📊 <b>Місячний звіт: {html.quote(obj['name'])}</b>\n"
        f"Період: {month_name} {year}\n\n"
        f"1️⃣ Введіть кількість згенерованої енергії за місяць (МВт*год):",
        parse_mode="HTML"
    )
    await callback.message.answer("Введіть число:", reply_markup=get_simple_cancel_kb())
    await callback.answer()

@router.message(MonthlyReportState.energy_mwh)
async def set_energy(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(",", "."))
        await state.update_data(energy_mwh=val)
        data = await state.get_data()
        
        if data.get('report_type') == 'corrector':
            await state.set_state(MonthlyReportState.gas_corrector_total)
            await message.answer("2. Показники газового коректора за місяць (м³):", reply_markup=get_simple_cancel_kb())
        else:
            await state.set_state(MonthlyReportState.gas_start)
            await message.answer("2.а) Показник газового лічильника на 1-ше число МИНУЛОГО місяця:", reply_markup=get_simple_cancel_kb())
    except ValueError:
        await message.answer("Будь ласка, введіть число.")

@router.message(MonthlyReportState.gas_corrector_total)
async def set_gas_corrector_total(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(",", "."))
        await state.update_data(gas_corrector_total=val)
        await state.set_state(MonthlyReportState.oil_start)
        await message.answer("3.а) Рівень оливи в баці на 1-ше число МИНУЛОГО місяця (л):", reply_markup=get_simple_cancel_kb())
    except ValueError:
        await message.answer("Будь ласка, введіть число.")

@router.message(MonthlyReportState.gas_start)
async def set_gas_start(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(",", "."))
        await state.update_data(gas_start=val)
        await state.set_state(MonthlyReportState.gas_end)
        await message.answer("2.б) Показник газового лічильника на СЬОГОДНІ:", reply_markup=get_simple_cancel_kb())
    except ValueError:
        await message.answer("Будь ласка, введіть число.")

@router.message(MonthlyReportState.gas_end)
async def set_gas_end(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(",", "."))
        await state.update_data(gas_end=val)
        await state.set_state(MonthlyReportState.gas_coef)
        await message.answer("2.в) Коефіцієнт газового коректора:", reply_markup=get_simple_cancel_kb())
    except ValueError:
        await message.answer("Будь ласка, введіть число.")

@router.message(MonthlyReportState.gas_coef)
async def set_gas_coef(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(",", "."))
        await state.update_data(gas_coef=val)
        await state.set_state(MonthlyReportState.oil_start)
        await message.answer("3.а) Рівень оливи в баці на 1-ше число МИНУЛОГО місяця (л):", reply_markup=get_simple_cancel_kb())
    except ValueError:
        await message.answer("Будь ласка, введіть число.")

@router.message(MonthlyReportState.oil_start)
async def set_oil_start(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(",", "."))
        await state.update_data(oil_start=val)
        await state.set_state(MonthlyReportState.oil_added)
        await message.answer("3.б) Скільки оливи було ДОЛИТО протягом місяця (л):", reply_markup=get_simple_cancel_kb())
    except ValueError:
        await message.answer("Будь ласка, введіть число.")

@router.message(MonthlyReportState.oil_added)
async def set_oil_added(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(",", "."))
        await state.update_data(oil_added=val)
        await state.set_state(MonthlyReportState.oil_end)
        await message.answer("3.в) Рівень оливи в баці на СЬОГОДНІ (л):", reply_markup=get_simple_cancel_kb())
    except ValueError:
        await message.answer("Будь ласка, введіть число.")

@router.message(MonthlyReportState.oil_end)
async def set_oil_end(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(",", "."))
        await state.update_data(oil_end=val)
        await show_monthly_preview(message, state)
    except ValueError:
        await message.answer("Будь ласка, введіть число.")

async def show_monthly_preview(message: Message, state: FSMContext):
    data = await state.get_data()
    report_type = data.get('report_type', 'difference')
    
    # Calculations
    if report_type == 'corrector':
        gas_total = data.get('gas_corrector_total', 0)
    else:
        gas_total = (data.get('gas_end', 0) - data.get('gas_start', 0)) * data.get('gas_coef', 1)
        
    oil_total = (data.get('oil_start', 0) + data.get('oil_added', 0)) - data.get('oil_end', 0)
    
    # Specific consumption (Resource / Energy)
    energy = data['energy_mwh']
    spec_gas = gas_total / energy if energy > 0 else 0
    spec_oil = oil_total / energy if energy > 0 else 0
    
    month_name, year = get_report_period_uk()
    # Find month index for DB
    months_map = {
        "Січень": 1, "Лютий": 2, "Березень": 3, "Квітень": 4,
        "Травень": 5, "Червень": 6, "Липень": 7, "Серпень": 8,
        "Вересень": 9, "Жовтень": 10, "Листопад": 11, "Грудень": 12
    }
    month_idx = months_map[month_name]

    await state.update_data(
        gas_total=round(gas_total, 2),
        oil_total=round(oil_total, 2),
        spec_gas=int(round(spec_gas)),
        spec_oil=round(spec_oil, 6),
        report_month=month_idx,
        report_year=year,
        report_period_str=f"{month_name} {year}"
    )

    if report_type == 'corrector':
        gas_info = f"2. Спожито газу (коректор): <code>{round(gas_total, 2)}</code> м³\n"
    else:
        gas_info = (
            f"2. Спожито газу: <code>{round(gas_total, 2)}</code> м³\n"
            f"   (Показники: {data['gas_start']} -> {data['gas_end']}, коєф: {data['gas_coef']})\n"
        )

    preview = (
        f"📊 <b>ПОПЕРЕДНІЙ ПЕРЕГЛЯД ЗВІТУ</b>\n"
        f"Об'єкт: {html.quote(data['tc_name'])}\n"
        f"Період: {month_name} {year}\n\n"
        f"1. Енергія: <code>{data['energy_mwh']}</code> МВт*год\n"
        f"{gas_info}"
        f"3. Олива на угар: <code>{round(oil_total, 2)}</code> л\n"
        f"   (Показники: {data['oil_start']} + долито {data['oil_added']} - {data['oil_end']})\n\n"
        f"4. Питома витрата газу: <code>{int(round(spec_gas))}</code> м³/МВт*год\n"
        f"5. Питома витрата оливи: <code>{round(spec_oil, 6)}</code> л/МВт*год\n\n"
        f"Зберегти та надіслати звіт?"
    )

    await state.set_state(MonthlyReportState.waiting_for_confirmation)
    await message.answer(preview, reply_markup=get_confirmation_kb("confirm_monthly", "cancel_monthly"), parse_mode="HTML")

@router.callback_query(MonthlyReportState.waiting_for_confirmation, F.data == "confirm_monthly")
async def handle_monthly_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user_id = callback.from_user.id
    user_data = await get_user(user_id)
    is_admin = user_id in config.admin_ids
    role = user_data['role'] if user_data else 'user'
    
    # Add user_id to data for DB
    data['user_id'] = user_id
    
    # Save to DB
    # Ensure all gas keys exist for DB even if using corrector type
    if data.get('report_type') == 'corrector':
        data['gas_start'] = 0
        data['gas_end'] = 0
        data['gas_coef'] = 0
        data['gas_total'] = data.get('gas_corrector_total', 0)

    await add_monthly_report(data)
    
    # Format final message for group
    report_msg = (
        f"📈 <b>МІСЯЧНИЙ ЗВІТ РОБОТИ ГПУ</b>\n"
        f"🏢 Об'єкт: <b>{html.quote(data['tc_name'])}</b>\n"
        f"📅 Період: {data['report_period_str']}\n"
        f"👤 Подав: {html.quote(user_data['full_name'] if user_data else callback.from_user.full_name)}\n"
        f"────────────────────\n"
        f"1️⃣ Згенеровано енергії: <b>{data['energy_mwh']}</b> МВт*год\n"
        f"2️⃣ Спожито газу за місяць: <b>{data['gas_total']}</b> м³\n"
        f"3️⃣ Олива на угар за місяць: <b>{data['oil_total']}</b> л\n"
        f"4️⃣ Питома витрата газу: <b>{data['spec_gas']}</b> м³/МВт*год\n"
        f"5️⃣ Питома витрата оливи: <b>{data['spec_oil']}</b> л/МВт*год\n"
        f"────────────────────\n"
        f"✅ Звіт прийнято."
    )

    # Send to object group
    obj = await get_object_by_id(data['object_id'])
    if obj and obj['telegram_group_id']:
        try:
            await bot.send_message(chat_id=obj['telegram_group_id'], text=report_msg, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Failed to send monthly report to group: {e}")

    # Also send to the specific monitoring group
    TARGET_GROUP_ID = -1003856935224
    try:
        await bot.send_message(chat_id=TARGET_GROUP_ID, text=report_msg, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Failed to send monthly report to target group {TARGET_GROUP_ID}: {e}")

    await state.clear()
    await callback.message.edit_text("✅ Місячний звіт успішно збережено та надіслано!")
    await callback.message.answer("Ви в головному меню.", reply_markup=get_main_menu_keyboard(is_admin=is_admin, role=role))
    await callback.answer()

@router.callback_query(MonthlyReportState.waiting_for_confirmation, F.data == "cancel_monthly")
async def handle_monthly_cancel(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_data = await get_user(user_id)
    is_admin = user_id in config.admin_ids
    role = user_data['role'] if user_data else 'user'
    
    await state.clear()
    await callback.message.edit_text("❌ Заповнення місячного звіту скасовано.")
    await callback.message.answer("Ви в головному меню.", reply_markup=get_main_menu_keyboard(is_admin=is_admin, role=role))
    await callback.answer()
