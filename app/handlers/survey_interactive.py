import logging
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from app.db.database import get_user, get_survey, add_survey_response, get_all_objects
from app.config import config
from app.states.survey_response import SurveyResponseState
from app.keyboards.inline import get_survey_user_skip_comment_kb

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data.startswith("survey_ans:"))
async def handle_survey_answer(callback: CallbackQuery, state: FSMContext, bot: Bot):
    parts = callback.data.split(":")
    survey_id = int(parts[1])
    answer = parts[2]

    user = await get_user(callback.from_user.id)
    full_name = user['full_name'] if user else callback.from_user.full_name

    # Try to find which object this group belongs to
    objects = await get_all_objects()
    obj_name = "Невідомий об'єкт"
    for obj in objects:
        if obj['telegram_group_id'] == callback.message.chat.id:
            obj_name = obj['name']
            break

    # --- BLOCK FURTHER RESPONSES ---
    # 1. Update the message to remove buttons and show who responded
    try:
        new_text_suffix = f"\n\n👤 <b>Відповів:</b> {full_name}"

        if callback.message.text:
            await callback.message.edit_text(
                text=callback.message.text + new_text_suffix,
                reply_markup=None,
                parse_mode="HTML"
            )
        elif callback.message.caption:
            await callback.message.edit_caption(
                caption=callback.message.caption + new_text_suffix,
                reply_markup=None,
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Failed to edit survey message: {e}")

    if answer == "no":
        await add_survey_response(survey_id, callback.from_user.id, full_name, obj_name, "no")
        
        # Notify summary group
        report_group_id = config.group_id
        monitor_msg = (
            f"❌ <b>ОПИТУВАННЯ: ВІДМОВА</b>\n\n"
            f"Об'єкт: <b>{obj_name}</b>\n"
            f"Оператор: <b>{full_name}</b>\n"
            f"Відповідь: <b>НІ</b>"
        )
        try:
            await bot.send_message(chat_id=report_group_id, text=monitor_msg, parse_mode="HTML")
            await callback.answer("Ваша відповідь 'НІ' врахована.", show_alert=True)
        except Exception as e:
            logger.error(f"Error sending survey 'no' notification: {e}")
    
    else: # answer == "yes"
        # Everything stays in the group now
        await state.update_data(
            survey_id=survey_id,
            survey_user_id=callback.from_user.id,
            survey_full_name=full_name,
            survey_obj_name=obj_name,
            survey_chat_id=callback.message.chat.id
        )
        await state.set_state(SurveyResponseState.waiting_for_photo)
        
        sent_instr = await callback.message.answer(
            f"📸 <b>{full_name}</b>, Ви обрали 'ТАК'.\nБудь ласка, надішліть <b>ФОТО</b> для підтвердження прямо сюди.",
            parse_mode="HTML"
        )
        await state.update_data(last_instr_msg_id=sent_instr.message_id)
        await callback.answer()

@router.message(SurveyResponseState.waiting_for_photo)
async def process_survey_user_photo(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    # Security: check if this is the same user who started the response
    if message.from_user.id != data.get("survey_user_id"):
        return # Ignore messages from other users in the group

    if not message.photo:
        # User sent text instead of photo
        sent_err = await message.answer("⚠️ Будь ласка, надішліть саме <b>ФОТО</b>.")
        # Optional: delete after a few seconds or track for deletion
        return

    photo_id = message.photo[-1].file_id
    await state.update_data(survey_user_photo=photo_id)
    
    # Delete previous instruction
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=data.get("last_instr_msg_id"))
    except: pass

    await state.set_state(SurveyResponseState.waiting_for_comment)
    sent_instr = await message.answer(
        "📝 Додайте коментар до вашої відповіді (або натисніть 'Пропустити'):",
        reply_markup=get_survey_user_skip_comment_kb()
    )
    await state.update_data(last_instr_msg_id=sent_instr.message_id)

@router.callback_query(SurveyResponseState.waiting_for_comment, F.data == "survey_user_skip_comment")
async def skip_survey_user_comment(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    if callback.from_user.id != data.get("survey_user_id"):
        await callback.answer("Це опитування заповнює інший користувач.", show_alert=True)
        return

    await state.update_data(survey_user_comment=None)
    await finalize_survey_response(callback.message, state, bot)
    await callback.answer()

@router.message(SurveyResponseState.waiting_for_comment)
async def process_survey_user_comment(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    if message.from_user.id != data.get("survey_user_id"):
        return

    await state.update_data(survey_user_comment=message.text)
    await finalize_survey_response(message, state, bot)

async def finalize_survey_response(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    survey_id = data.get('survey_id')
    user_id = data.get('survey_user_id')
    full_name = data.get('survey_full_name')
    obj_name = data.get('survey_obj_name')
    photo_id = data.get('survey_user_photo')
    comment = data.get('survey_user_comment')
    instr_msg_id = data.get('last_instr_msg_id')
    
    # Delete instruction message
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=instr_msg_id)
    except: pass

    if not survey_id:
        await message.answer("⚠️ Помилка: дані опитування втрачені.")
        await state.clear()
        return

    await add_survey_response(survey_id, user_id, full_name, obj_name, "yes", photo_id, comment)
    
    # Notify summary group
    report_group_id = config.group_id
    monitor_msg = (
        f"✅ <b>НОВИЙ ВІДГУК НА ОПИТУВАННЯ</b>\n\n"
        f"Об'єкт: <b>{obj_name}</b>\n"
        f"Користувач: <b>{full_name}</b>\n"
        f"Відповідь: <b>ТАК</b>\n"
        f"Коментар: {comment if comment else 'Відсутній'}"
    )
    
    try:
        await bot.send_photo(chat_id=report_group_id, photo=photo_id, caption=monitor_msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error sending survey 'yes' notification: {e}")
    
    await message.answer(f"✅ Дякуємо, <b>{full_name}</b>! Ваша відповідь відправлена.", parse_mode="HTML")
    await state.clear()
