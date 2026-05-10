import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from app.db.database import get_user, get_schedule_by_id
from app.config import config
from app.states.reminder_comment import ReminderCommentStates

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data.startswith("remind_ignore:"))
async def handle_remind_ignore(callback: CallbackQuery, bot: Bot):
    """Handles 'Ignore' button in reminders."""
    data_parts = callback.data.split(':')
    if len(data_parts) < 4:
        return

    schedule_id = int(data_parts[1])
    event_type = data_parts[2]
    event_time = data_parts[3]

    # 1. Get user info
    user = await get_user(callback.from_user.id)
    full_name = user['full_name'] if user else callback.from_user.full_name

    # 2. Get schedule/object info
    sched = await get_schedule_by_id(schedule_id)
    obj_name = sched['tc_name'] if sched else "Невідомий об'єкт"
    action = "запуску" if event_type == 'start' else "зупинки"

    # 3. Notify monitoring group
    report_group_id = config.group_id
    monitor_msg = (
        f"🔇 <b>Скасування нагадування</b>\n\n"
        f"Об'єкт: <b>{obj_name}</b>\n"
        f"Подія: {action} о {event_time}\n"
        f"Оператор: <b>{full_name}</b>\n"
        f"Статус: <b>Ігноровано</b> (звіт не буде подано)"
    )
    
    try:
        await bot.send_message(chat_id=report_group_id, text=monitor_msg, parse_mode="HTML")
        # Update original message to remove buttons
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer("Нагадування скасовано. Моніторинг сповіщено.", show_alert=True)
    except Exception as e:
        logger.error(f"Error in handle_remind_ignore: {e}")
        await callback.answer("Помилка при обробці.", show_alert=True)

@router.callback_query(F.data.startswith("remind_comment:"))
async def handle_remind_comment_start(callback: CallbackQuery, state: FSMContext):
    """Starts the 'Leave comment' flow."""
    data_parts = callback.data.split(':')
    if len(data_parts) < 4:
        return

    schedule_id = int(data_parts[1])
    event_type = data_parts[2]
    event_time = data_parts[3]

    # Save info in state
    await state.update_data(
        remind_schedule_id=schedule_id,
        remind_event_type=event_type,
        remind_event_time=event_time,
        remind_msg_id=callback.message.message_id,
        remind_chat_id=callback.message.chat.id
    )

    await state.set_state(ReminderCommentStates.waiting_for_comment)
    await callback.answer()
    
    cancel_msg = "☝️ <b>Напишіть причину</b>, чому звіт не було подано (можна додати фото).\n\n<i>Для скасування натисніть /cancel</i>"
    await callback.message.answer(cancel_msg, parse_mode="HTML")

@router.message(ReminderCommentStates.waiting_for_comment)
async def handle_remind_comment_input(message: Message, state: FSMContext, bot: Bot):
    """Receives text/photo comment and forwards to monitor group."""
    state_data = await state.get_data()
    schedule_id = state_data.get('remind_schedule_id')
    event_type = state_data.get('remind_event_type')
    event_time = state_data.get('remind_event_time')
    orig_msg_id = state_data.get('remind_msg_id')
    orig_chat_id = state_data.get('remind_chat_id')

    # 1. Get user info
    user = await get_user(message.from_user.id)
    full_name = user['full_name'] if user else message.from_user.full_name

    # 2. Get schedule/object info
    sched = await get_schedule_by_id(schedule_id)
    obj_name = sched['tc_name'] if sched else "Невідомий об'єкт"
    action = "запуску" if event_type == 'start' else "зупинки"

    comment_text = message.text or message.caption or "(без тексту)"
    
    # 3. Notify monitoring group
    report_group_id = config.group_id
    monitor_header = (
        f"💬 <b>Коментар до нагадування</b>\n\n"
        f"Об'єкт: <b>{obj_name}</b>\n"
        f"Подія: {action} о {event_time}\n"
        f"Оператор: <b>{full_name}</b>\n\n"
        f"Текст: {comment_text}"
    )

    try:
        if message.photo:
            photo_id = message.photo[-1].file_id
            await bot.send_photo(chat_id=report_group_id, photo=photo_id, caption=monitor_header, parse_mode="HTML")
        else:
            await bot.send_message(chat_id=report_group_id, text=monitor_header, parse_mode="HTML")

        # Update original reminder to remove buttons
        try:
            await bot.edit_message_reply_markup(chat_id=orig_chat_id, message_id=orig_msg_id, reply_markup=None)
        except: pass

        await message.answer("✅ Ваш коментар надіслано в групу моніторингу.")
        await state.clear()
    except Exception as e:
        logger.error(f"Error in handle_remind_comment_input: {e}")
        await message.answer("❌ Сталася помилка при відправці. Спробуйте пізніше.")
