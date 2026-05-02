import logging
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from app.db.database import (
    get_user_objects_by_tg_id, get_object_by_id, get_user,
    start_shift, end_shift, get_active_shift, get_predecessor_shift,
    set_planned_end_time, get_setting, update_setting
)
from app.states.shifts import ShiftState
from app.keyboards.reply import get_shift_actions_kb, get_main_menu_keyboard
from app.keyboards.inline import (
    get_object_selection_kb, get_predecessor_confirm_kb, 
    get_shift_action_confirm_kb, get_hour_selection_kb, get_minute_selection_kb
)
from app.config import config

router = Router()

@router.message(F.text == "👤 Керування змінами")
async def cmd_shifts_start(message: Message, state: FSMContext):
    user_objs = await get_user_objects_by_tg_id(message.from_user.id)
    
    if not user_objs:
        await message.answer("❌ За вами не закріплено жодного об'єкта. Зверніться до адміністратора.")
        return

    if len(user_objs) == 1:
        obj = user_objs[0]
        await state.update_data(object_id=obj['id'], object_name=obj['name'])
        await message.answer(
            f"🏢 Об'єкт: <b>{obj['name']}</b>\nОберіть дію:",
            reply_markup=get_shift_actions_kb(),
            parse_mode="HTML"
        )
        await state.set_state(ShiftState.choosing_action)
    else:
        await message.answer(
            "Оберіть об'єкт для керування зміною:",
            reply_markup=get_object_selection_kb(user_objs),
            parse_mode="HTML"
        )
        await state.set_state(ShiftState.choosing_object)

@router.callback_query(ShiftState.choosing_object, F.data.startswith("select_obj:"))
async def shift_object_selected(callback: CallbackQuery, state: FSMContext):
    obj_id = int(callback.data.split(":")[1])
    obj = await get_object_by_id(obj_id)
    
    await state.update_data(object_id=obj_id, object_name=obj['name'])
    await callback.message.edit_text(
        f"🏢 Об'єкт: <b>{obj['name']}</b>\nОберіть дію:",
        reply_markup=get_shift_actions_kb_inline(obj_id),
        parse_mode="HTML"
    )
    await state.set_state(ShiftState.choosing_action)

def get_shift_actions_kb_inline(obj_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍🔧 Ваша зміна почалась?", callback_data=f"shift_start_btn:{obj_id}")],
        [InlineKeyboardButton(text="🏁 Ваша зміна закінчилась?", callback_data=f"shift_end_btn:{obj_id}")],
        [InlineKeyboardButton(text="❌ Відміна", callback_data="cancel_checklist")]
    ])

@router.message(ShiftState.choosing_action, F.text.contains("почалась"))
@router.callback_query(F.data.startswith("shift_start_btn:"))
async def handle_shift_start_request(event: Message | CallbackQuery, state: FSMContext):
    data = await state.get_data()
    obj_id = data.get('object_id')
    
    # Recovery logic if state was lost (e.g. after bot restart)
    if not obj_id:
        if isinstance(event, CallbackQuery):
            try:
                obj_id = int(event.data.split(":")[1])
            except: pass
        else:
            # Try to recover if user has only one object
            user_objs = await get_user_objects_by_tg_id(event.from_user.id)
            if len(user_objs) == 1:
                obj_id = user_objs[0]['id']
                await state.update_data(object_id=obj_id, object_name=user_objs[0]['name'])

    if not obj_id:
        msg = "❌ Помилка: сесія застаріла або об'єкт не обрано. Будь ласка, натисніть кнопку 👤 <b>Керування змінами</b> ще раз."
        if isinstance(event, Message): await event.answer(msg, parse_mode="HTML")
        else: await event.answer(msg, show_alert=True)
        return

    # Get current user's DB name
    user_db = await get_user(event.from_user.id)
    user_name = user_db['full_name'] if user_db else event.from_user.full_name

    # Check if ALREADY on shift
    active = await get_active_shift(event.from_user.id, obj_id)
    if active:
        msg = "⚠️ Ви вже перебуваєте на зміні на цьому об'єкті."
        if isinstance(event, Message): await event.answer(msg)
        else: await event.answer(msg, show_alert=True)
        return

    # Check for predecessor
    predecessor = await get_predecessor_shift(obj_id, event.from_user.id)
    
    if predecessor:
        # Notify predecessor
        bot = event.bot
        try:
            obj_name = data.get('object_name')
            if not obj_name:
                obj_data = await get_object_by_id(obj_id)
                obj_name = obj_data['name'] if obj_data else "Об'єкт"
                
            pred_msg = (
                f"👨‍🔧 <b>{user_name}</b> заступає на зміну на об'єкті <b>{obj_name}</b>.\n"
                f"Чи бажаєте завершити свою зміну?"
            )
            await bot.send_message(
                chat_id=predecessor['user_id'],
                text=pred_msg,
                reply_markup=get_predecessor_confirm_kb(obj_id),
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Failed to notify predecessor {predecessor['user_id']}: {e}")

    # Start new shift
    await start_shift(event.from_user.id, obj_id)
    
    # Get obj name for success message
    obj_name = data.get('object_name')
    if not obj_name:
        obj_data = await get_object_by_id(obj_id)
        obj_name = obj_data['name'] if obj_data else "Об'єкт"

    success_msg = f"✅ Ви заступили на зміну (Об'єкт: {obj_name}). Успішної роботи!"
    if isinstance(event, Message):
        await event.answer(success_msg, reply_markup=get_main_menu_keyboard(role='user'))
    else:
        await event.message.edit_text(success_msg)
        await event.answer()

    # Notify Group
    obj = await get_object_by_id(obj_id)
    if obj and obj.get('telegram_group_id'):
        group_msg = f"👨‍🔧 <b>{user_name}</b> заступив на зміну."
        try:
            await event.bot.send_message(chat_id=obj['telegram_group_id'], text=group_msg, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Failed to send shift start notification to group {obj['telegram_group_id']}: {e}")

    await state.clear()

@router.message(ShiftState.choosing_action, F.text.contains("закінчилась"))
@router.callback_query(F.data.startswith("shift_end_btn:"))
async def handle_shift_end_request(event: Message | CallbackQuery, state: FSMContext):
    data = await state.get_data()
    obj_id = data.get('object_id')
    
    if not obj_id:
        if isinstance(event, CallbackQuery):
            try:
                obj_id = int(event.data.split(":")[1])
            except: pass
        else:
            user_objs = await get_user_objects_by_tg_id(event.from_user.id)
            if len(user_objs) == 1:
                obj_id = user_objs[0]['id']

    if not obj_id:
        msg = "❌ Помилка: об'єкт не знайдено. Будь ласка, почніть процес заново через меню 👤 <b>Керування змінами</b>."
        if isinstance(event, Message): await event.answer(msg, parse_mode="HTML")
        else: await event.answer(msg, show_alert=True)
        return
    
    active = await get_active_shift(event.from_user.id, obj_id)
    if not active:
        msg = "❌ У вас немає активної зміни на цьому об'єкті."
        if isinstance(event, Message): await event.answer(msg)
        else: await event.answer(msg, show_alert=True)
        return

    await end_shift(event.from_user.id, obj_id)
    
    msg = "🏁 Зміну закрито."
    if isinstance(event, Message):
        await event.answer(msg, reply_markup=get_main_menu_keyboard(role='user'))
    else:
        await event.message.edit_text(msg)
        await event.answer()

    # Notify Group
    obj = await get_object_by_id(obj_id)
    user_db = await get_user(event.from_user.id)
    user_name = user_db['full_name'] if user_db else event.from_user.full_name
    
    if obj.get('telegram_group_id'):
        group_msg = f"🏁 <b>{user_name}</b> зміну здав!"
        try:
            await event.bot.send_message(chat_id=obj['telegram_group_id'], text=group_msg, parse_mode="HTML")
        except: pass

    await state.clear()

# --- Predecessor Handover Callbacks ---

@router.callback_query(F.data.startswith("shift_handover:"))
async def process_handover(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    obj_id = int(parts[1])
    answer = parts[2]
    
    if answer == "yes":
        await end_shift(callback.from_user.id, obj_id)
        await callback.message.edit_text("✅ Зміну завершено. Дякуємо!")
        
        # Notify Group about handover
        obj = await get_object_by_id(obj_id)
        user_db = await get_user(callback.from_user.id)
        user_name = user_db['full_name'] if user_db else callback.from_user.full_name
        
        if obj.get('telegram_group_id'):
            group_msg = f"🏁 <b>{user_name}</b> зміну здав! (перезмінка)"
            try:
                await callback.bot.send_message(chat_id=obj['telegram_group_id'], text=group_msg, parse_mode="HTML")
            except: pass
    else:
        # User stays on shift, ask until when
        await callback.message.edit_text(
            "Виберіть час до якого ви плануєте залишатись на зміні:",
            reply_markup=get_hour_selection_kb()
        )
        await state.update_data(handover_obj_id=obj_id)
        await state.set_state(ShiftState.choosing_planned_end)

@router.callback_query(ShiftState.choosing_planned_end, F.data.startswith("select_hour_"))
async def shift_hour_selected(callback: CallbackQuery, state: FSMContext):
    hour = callback.data.split("_")[2]
    await state.update_data(planned_h=hour)
    await callback.message.edit_text(
        f"Вибрана година: {hour}. Тепер оберіть хвилини:",
        reply_markup=get_minute_selection_kb(int(hour))
    )

@router.callback_query(ShiftState.choosing_planned_end, F.data.startswith("select_minute_"))
async def shift_minute_selected(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    h, m = parts[2], parts[3]
    time_str = f"{h}:{m}"
    
    data = await state.get_data()
    obj_id = data.get('handover_obj_id')
    
    active = await get_active_shift(callback.from_user.id, obj_id)
    if active:
        await set_planned_end_time(active['id'], time_str)
        await callback.message.edit_text(f"🕒 Записано. Ми нагадаємо вам о {time_str} завершити зміну.")
    else:
        await callback.message.edit_text("❌ Помилка: активну зміну не знайдено.")
    
    await state.clear()
