import logging
import asyncio
import json
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove, InputMediaPhoto
from aiogram.fsm.context import FSMContext

from app.db.database import get_user, get_survey, add_survey_response, get_all_objects
from app.config import config
from app.states.survey_response import SurveyResponseState
from app.keyboards.inline import get_survey_user_skip_comment_kb, get_survey_user_done_photos_kb

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
            
        # Trigger export to Google Sheets
        try:
            from export_to_google import export_survey_response_task
            asyncio.create_task(export_survey_response_task(bot, survey_id, full_name, obj_name, "НІ", [], None))
        except Exception as e:
            logger.error(f"Failed to trigger google export task for 'no': {e}")
    
    else: # answer == "yes"
        # Everything stays in the group now
        await state.update_data(
            survey_id=survey_id,
            survey_user_id=callback.from_user.id,
            survey_full_name=full_name,
            survey_obj_name=obj_name,
            survey_chat_id=callback.message.chat.id,
            survey_user_photos=[]
        )
        await state.set_state(SurveyResponseState.waiting_for_photo)
        
        sent_instr = await callback.message.answer(
            f"📸 <b>{full_name}</b>, Ви обрали 'ТАК'.\nБудь ласка, надішліть від 1 до 5 <b>ФОТО</b> для підтвердження прямо сюди.",
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
        await message.answer("⚠️ Будь ласка, надішліть саме <b>ФОТО</b>.")
        return

    photo_id = message.photo[-1].file_id
    photos = data.get("survey_user_photos", [])
    photos.append(photo_id)
    await state.update_data(survey_user_photos=photos)
    
    # Delete previous instruction
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=data.get("last_instr_msg_id"))
    except: pass

    # Optional: Delete user's photo message to keep chat clean (optional, can keep)
    
    if len(photos) >= 5:
        await state.set_state(SurveyResponseState.waiting_for_comment)
        sent_instr = await message.answer(
            f"✅ Отримано максимальну кількість фото ({len(photos)}/5).\n\n📝 Додайте коментар до вашої відповіді (або натисніть 'Пропустити'):",
            reply_markup=get_survey_user_skip_comment_kb()
        )
        await state.update_data(last_instr_msg_id=sent_instr.message_id)
    else:
        sent_instr = await message.answer(
            f"✅ Фото отримано ({len(photos)}/5). Можете надіслати ще або натиснути кнопку нижче, щоб перейти до коментаря.",
            reply_markup=get_survey_user_done_photos_kb()
        )
        await state.update_data(last_instr_msg_id=sent_instr.message_id)

@router.callback_query(SurveyResponseState.waiting_for_photo, F.data == "survey_user_done_photos")
async def process_survey_user_done_photos(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    if callback.from_user.id != data.get("survey_user_id"):
        await callback.answer("Це опитування заповнює інший користувач.", show_alert=True)
        return
        
    photos = data.get("survey_user_photos", [])
    if not photos:
        await callback.answer("⚠️ Надішліть хоча б одне фото перед продовженням!", show_alert=True)
        return
        
    # Delete previous instruction
    try:
        await bot.delete_message(chat_id=callback.message.chat.id, message_id=data.get("last_instr_msg_id"))
    except: pass
    
    await state.set_state(SurveyResponseState.waiting_for_comment)
    sent_instr = await callback.message.answer(
        "📝 Додайте коментар до вашої відповіді (або натисніть 'Пропустити'):",
        reply_markup=get_survey_user_skip_comment_kb()
    )
    await state.update_data(last_instr_msg_id=sent_instr.message_id)
    await callback.answer()

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
    photos = data.get('survey_user_photos', [])
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

    # Save to database, serializing photo list as json
    photo_ids_json = json.dumps(photos) if photos else None
    await add_survey_response(survey_id, user_id, full_name, obj_name, "yes", photo_ids_json, comment)
    
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
        if photos:
            if len(photos) == 1:
                await bot.send_photo(chat_id=report_group_id, photo=photos[0], caption=monitor_msg, parse_mode="HTML")
            else:
                media = [InputMediaPhoto(media=p) for p in photos]
                media[0].caption = monitor_msg
                media[0].parse_mode = "HTML"
                await bot.send_media_group(chat_id=report_group_id, media=media)
        else:
            await bot.send_message(chat_id=report_group_id, text=monitor_msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error sending survey notification: {e}")
    
    # Trigger export to Google Sheets (we'll implement this task next)
    try:
        from export_to_google import export_survey_response_task
        asyncio.create_task(export_survey_response_task(bot, survey_id, full_name, obj_name, "ТАК", photos, comment))
    except Exception as e:
        logger.error(f"Failed to trigger google export task: {e}")
        
    await message.answer(f"✅ Дякуємо, <b>{full_name}</b>! Ваша відповідь відправлена.", parse_mode="HTML")
    await state.clear()
