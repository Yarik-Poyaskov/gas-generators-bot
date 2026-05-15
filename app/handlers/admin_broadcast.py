import asyncio
import logging
import json
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from app.config import config
from app.filters.is_admin import IsAdmin
from app.db.database import (
    get_all_objects, create_broadcast, add_broadcast_message, 
    get_broadcast, get_broadcast_messages, update_broadcast_text,
    update_broadcast_pin_status, delete_broadcast_from_db,
    get_all_broadcasts, count_broadcasts,
    create_survey, add_survey_message, get_survey, get_survey_messages,
    get_all_surveys, count_surveys, delete_survey_from_db, get_survey_responses
)
from app.keyboards.inline import (
    get_broadcast_main_kb, get_broadcast_preview_kb,
    get_broadcast_archive_kb, get_broadcast_manage_kb,
    get_survey_skip_photo_kb, get_survey_preview_kb, get_survey_action_kb,
    get_survey_archive_kb, get_survey_manage_kb, get_survey_objects_kb
)
from app.keyboards.reply import get_admin_main_keyboard, get_simple_cancel_kb
from app.states.admin import BroadcastState, SurveyState

logger = logging.getLogger(__name__)
router = Router()
# Note: We will apply filters selectively to allow user responses later, 
# but for now creation is for Admins.
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

@router.message(F.text == "Розсилка")
async def cmd_broadcast_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "📢 <b>Керування розсилками</b>\n\nВи можете створити нове повідомлення для всіх груп об'єктів або переглянути архів.",
        reply_markup=get_broadcast_main_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "bc_main")
async def callback_broadcast_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "📢 <b>Керування розсилками</b>\n\nВи можете створити нове повідомлення для всіх груп об'єктів або переглянути архів.",
        reply_markup=get_broadcast_main_kb(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "bc_create")
async def start_broadcast_creation(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastState.waiting_for_content)
    await callback.message.answer(
        "📝 <b>Надішліть текст розсилки.</b>\n\nМожна додати одну картинку до повідомлення. "
        "Коли будете готові, бот покаже передперегляд.",
        reply_markup=get_simple_cancel_kb(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(BroadcastState.waiting_for_content)
async def process_broadcast_content(message: Message, state: FSMContext):
    if message.text == "Відміна":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=get_admin_main_keyboard())
        return

    text = message.text or message.caption
    photo_id = message.photo[-1].file_id if message.photo else None
    
    if not text and not photo_id:
        await message.answer("⚠️ Повідомлення порожнє. Будь ласка, надішліть текст або фото з текстом.")
        return

    await state.update_data(bc_text=text, bc_photo=photo_id)
    await state.set_state(BroadcastState.confirming)
    
    await message.answer("👀 <b>Передперегляд розсилки:</b>", reply_markup=get_admin_main_keyboard(), parse_mode="HTML")
    
    if photo_id:
        await message.answer_photo(photo=photo_id, caption=text, reply_markup=get_broadcast_preview_kb(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=get_broadcast_preview_kb(), parse_mode="HTML")

@router.callback_query(BroadcastState.confirming, F.data.startswith("bc_send:"))
async def send_broadcast_logic(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    text = data.get("bc_text")
    photo_id = data.get("bc_photo")
    pin_mode = callback.data.split(":")[1] == "pinned"
    
    # 1. Create broadcast in DB
    bc_id = await create_broadcast(callback.from_user.id, text, photo_id)
    
    # 2. Get all objects with unique groups
    objects = await get_all_objects()
    target_groups = list(set(obj['telegram_group_id'] for obj in objects if obj['telegram_group_id']))
    
    if not target_groups:
        await callback.answer("⚠️ Немає груп для розсилки!", show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None)
    status_msg = await callback.message.answer(f"🚀 Починаю розсилку на {len(target_groups)} груп...")
    
    success_count = 0
    for group_id in target_groups:
        try:
            if photo_id:
                sent = await bot.send_photo(chat_id=group_id, photo=photo_id, caption=text, parse_mode="HTML")
            else:
                sent = await bot.send_message(chat_id=group_id, text=text, parse_mode="HTML")
            
            await add_broadcast_message(bc_id, group_id, sent.message_id)
            
            if pin_mode:
                try:
                    await bot.pin_chat_message(chat_id=group_id, message_id=sent.message_id, disable_notification=True)
                except: pass
            
            success_count += 1
            await asyncio.sleep(0.1) # Small delay to avoid flood
        except Exception as e:
            logger.error(f"Failed to send broadcast to {group_id}: {e}")

    await update_broadcast_pin_status(bc_id, pin_mode)
    await status_msg.edit_text(f"✅ <b>Розсилка завершена!</b>\nУспішно: {success_count}/{len(target_groups)}", parse_mode="HTML")
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "bc_cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("Розсилку скасовано.", reply_markup=get_admin_main_keyboard())
    await callback.answer()

# --- Archive and Management ---

@router.callback_query(F.data.startswith("bc_archive:"))
async def view_broadcast_archive(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    per_page = config.users_per_page
    
    total_count = await count_broadcasts()
    broadcasts = await get_all_broadcasts(limit=per_page, offset=page * per_page)
    
    total_pages = (total_count + per_page - 1) // per_page
    
    text = f"📂 <b>Архів розсилок</b> (Всього: {total_count})"
    if not broadcasts:
        text = "📂 Архів порожній."
        
    await callback.message.edit_text(
        text, 
        reply_markup=get_broadcast_archive_kb(broadcasts, page, total_pages),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("bc_view:"))
async def view_single_broadcast(callback: CallbackQuery):
    bc_id = int(callback.data.split(":")[1])
    bc = await get_broadcast(bc_id)
    if not bc:
        await callback.answer("Розсилку не знайдено.", show_alert=True)
        return
        
    msgs = await get_broadcast_messages(bc_id)
    is_pinned = any(m['is_pinned'] for m in msgs)
    
    text = f"📄 <b>Деталі розсилки #{bc_id}</b>\n"
    text += f"📅 Дата: {bc['created_at']}\n"
    text += f"👥 Отримувачів: {len(msgs)}\n"
    text += f"📌 Закріплено: {'Так' if is_pinned else 'Ні'}\n\n"
    text += f"📝 <b>Текст:</b>\n{bc['text'] or '[Без тексту]'}"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_broadcast_manage_kb(bc_id, is_pinned),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("bc_edit:"))
async def edit_broadcast_start(callback: CallbackQuery, state: FSMContext):
    bc_id = int(callback.data.split(":")[1])
    await state.update_data(editing_bc_id=bc_id)
    await state.set_state(BroadcastState.editing_existing)
    await callback.message.answer(
        "✏️ <b>Введіть новий текст для розсилки.</b>\nФото залишиться тим самим.",
        reply_markup=get_simple_cancel_kb(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(BroadcastState.editing_existing)
async def process_broadcast_edit_text(message: Message, state: FSMContext, bot: Bot):
    if message.text == "Відміна":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=get_admin_main_keyboard())
        return

    data = await state.get_data()
    bc_id = data['editing_bc_id']
    new_text = message.text
    
    bc = await get_broadcast(bc_id)
    msgs = await get_broadcast_messages(bc_id)
    
    status_msg = await message.answer(f"🔄 Оновлюю текст у {len(msgs)} чатах...")
    
    success_count = 0
    for m in msgs:
        try:
            if bc['photo_id']:
                await bot.edit_message_caption(chat_id=m['chat_id'], message_id=m['message_id'], caption=new_text, parse_mode="HTML")
            else:
                await bot.edit_message_text(chat_id=m['chat_id'], message_id=m['message_id'], text=new_text, parse_mode="HTML")
            success_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Failed to edit message {m['message_id']} in {m['chat_id']}: {e}")

    await update_broadcast_text(bc_id, new_text)
    await status_msg.edit_text(f"✅ <b>Текст оновлено!</b>\nУспішно: {success_count}/{len(msgs)}", parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data.startswith("bc_pin:"))
async def process_broadcast_pin(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split(":")
    bc_id, action = int(parts[1]), parts[2]
    
    msgs = await get_broadcast_messages(bc_id)
    status_text = "Закріплюю" if action == "pin" else "Відкріплюю"
    await callback.answer(f"{status_text} повідомлення...")
    
    success_count = 0
    for m in msgs:
        try:
            if action == "pin":
                await bot.pin_chat_message(chat_id=m['chat_id'], message_id=m['message_id'], disable_notification=True)
            else:
                await bot.unpin_chat_message(chat_id=m['chat_id'], message_id=m['message_id'])
            success_count += 1
            await asyncio.sleep(0.05)
        except: pass
        
    await update_broadcast_pin_status(bc_id, action == "pin")
    await view_single_broadcast(callback)

@router.callback_query(F.data.startswith("bc_delete:"))
async def process_broadcast_delete(callback: CallbackQuery, bot: Bot):
    bc_id = int(callback.data.split(":")[1])
    
    # Optional: Confirmation before deletion
    # But for now, direct deletion as requested
    
    msgs = await get_broadcast_messages(bc_id)
    await callback.answer("Видаляю розсилку...")
    
    for m in msgs:
        try:
            await bot.delete_message(chat_id=m['chat_id'], message_id=m['message_id'])
            await asyncio.sleep(0.05)
        except: pass
        
    await delete_broadcast_from_db(bc_id)
    await view_broadcast_archive(callback)

# --- Survey 1 (Опитувальник 1) ---

@router.callback_query(F.data == "bc_survey")
async def start_survey_creation(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SurveyState.waiting_for_text)
    await callback.message.answer(
        "📝 <b>Опитувальник 1: Крок 1</b>\n\nВведіть текст опитування (запитання).",
        reply_markup=get_simple_cancel_kb(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(SurveyState.waiting_for_text)
async def process_survey_text(message: Message, state: FSMContext):
    if message.text == "Відміна":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=get_admin_main_keyboard())
        return

    await state.update_data(survey_text=message.text)
    await state.set_state(SurveyState.waiting_for_photos)
    await message.answer(
        "🖼 <b>Опитувальник 1: Крок 2</b>\n\nНадішліть одне або кілька фото для опитування. "
        "Коли закінчите, натисніть кнопку для передперегляду.",
        reply_markup=get_survey_skip_photo_kb(),
        parse_mode="HTML"
    )

@router.message(SurveyState.waiting_for_photos, F.photo)
async def process_survey_photos(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("survey_photos", [])
    photos.append(message.photo[-1].file_id)
    await state.update_data(survey_photos=photos)
    
    await message.answer(
        f"✅ Фото отримано ({len(photos)}). Можете надіслати ще або натиснути кнопку для перегляду результату.",
        reply_markup=get_survey_preview_kb()
    )

@router.callback_query(SurveyState.waiting_for_photos, F.data == "survey_skip_photo")
async def skip_survey_photos(callback: CallbackQuery, state: FSMContext):
    # Check if we already warned
    data = await state.get_data()
    if not data.get("photo_skip_warned"):
        await state.update_data(photo_skip_warned=True)
        await callback.message.answer(
            "⚠️ <b>Попередження:</b> Фото дуже бажане для цього опитування. "
            "Ви впевнені, що хочете продовжити без фото?",
            reply_markup=get_survey_skip_photo_kb(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    await state.update_data(survey_photos=[])
    await show_survey_summary(callback.message, state)
    await callback.answer()

from aiogram.types import Message, CallbackQuery, InputMediaPhoto, ContentType, ReplyKeyboardRemove

@router.callback_query(SurveyState.waiting_for_photos, F.data == "survey_send")
async def start_survey_object_selection(callback: CallbackQuery, state: FSMContext):
    """Step 3: Select target groups."""
    objects = await get_all_objects()
    # Filter only objects with group_id
    valid_objects = [obj for obj in objects if obj['telegram_group_id']]
    
    if not valid_objects:
        await callback.answer("⚠️ Немає об'єктів з прив'язаними групами!", show_alert=True)
        return
        
    # Default: select all
    data = await state.get_data()
    selected_ids = data.get("selected_object_ids")
    if selected_ids is None:
        selected_ids = [obj['telegram_group_id'] for obj in valid_objects]
        await state.update_data(selected_object_ids=selected_ids)
        
    await state.set_state(SurveyState.waiting_for_objects)
    
    await callback.message.answer(
        "🎯 <b>Опитування: Крок 3</b>\n\nОберіть групи, в які потрібно надіслати опитування:",
        reply_markup=get_survey_objects_kb(valid_objects, selected_ids),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(SurveyState.waiting_for_objects, F.data.startswith("survey_toggle_obj:"))
async def toggle_survey_object(callback: CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    selected_ids = data.get("selected_object_ids", [])
    
    if group_id in selected_ids:
        selected_ids.remove(group_id)
    else:
        selected_ids.append(group_id)
        
    await state.update_data(selected_object_ids=selected_ids)
    
    objects = await get_all_objects()
    valid_objects = [obj for obj in objects if obj['telegram_group_id']]
    
    await callback.message.edit_reply_markup(
        reply_markup=get_survey_objects_kb(valid_objects, selected_ids)
    )
    await callback.answer()

@router.callback_query(SurveyState.waiting_for_objects, F.data == "survey_select_all")
async def survey_select_all_objects(callback: CallbackQuery, state: FSMContext):
    objects = await get_all_objects()
    valid_objects = [obj for obj in objects if obj['telegram_group_id']]
    selected_ids = [obj['telegram_group_id'] for obj in valid_objects]
    
    await state.update_data(selected_object_ids=selected_ids)
    await callback.message.edit_reply_markup(
        reply_markup=get_survey_objects_kb(valid_objects, selected_ids)
    )
    await callback.answer()

@router.callback_query(SurveyState.waiting_for_objects, F.data == "survey_deselect_all")
async def survey_deselect_all_objects(callback: CallbackQuery, state: FSMContext):
    await state.update_data(selected_object_ids=[])
    objects = await get_all_objects()
    valid_objects = [obj for obj in objects if obj['telegram_group_id']]
    
    await callback.message.edit_reply_markup(
        reply_markup=get_survey_objects_kb(valid_objects, [])
    )
    await callback.answer()

@router.callback_query(SurveyState.waiting_for_objects, F.data == "survey_confirm_send")
async def survey_preview_step(callback: CallbackQuery, state: FSMContext):
    """Step 4: Preview before final send."""
    data = await state.get_data()
    target_groups = data.get("selected_object_ids", [])
    
    if not target_groups:
        await callback.answer("⚠️ Оберіть хоча б одну групу!", show_alert=True)
        return
        
    await show_survey_summary(callback.message, state)
    await callback.answer()

async def show_survey_summary(message: Message, state: FSMContext):
    data = await state.get_data()
    text = data.get("survey_text")
    photos = data.get("survey_photos", [])
    target_groups = data.get("selected_object_ids", [])
    
    await state.set_state(SurveyState.confirming)
    
    summary_text = f"👀 <b>Передперегляд опитування:</b>\n🎯 Буде відправлено у <b>{len(target_groups)}</b> груп."
    
    # Hide the main keyboard during preview
    await message.answer(summary_text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    
    if photos:
        if len(photos) == 1:
            await message.answer_photo(photo=photos[0], caption=text, reply_markup=get_survey_preview_kb(), parse_mode="HTML")
        else:
            media = [InputMediaPhoto(media=p) for p in photos]
            media[0].caption = text
            media[0].parse_mode = "HTML"
            await message.answer_media_group(media=media)
            await message.answer("👆 Опитування вище. Натисніть кнопку для фінальної відправки:", reply_markup=get_survey_preview_kb())
    else:
        await message.answer(text, reply_markup=get_survey_preview_kb(), parse_mode="HTML")

@router.callback_query(SurveyState.confirming, F.data == "survey_send")
async def send_survey_logic(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    text = data.get("survey_text")
    photos = data.get("survey_photos", [])
    target_groups = data.get("selected_object_ids", [])
    
    if not target_groups:
        await callback.answer("⚠️ Оберіть хоча б одну групу!", show_alert=True)
        return
        
    # 1. Create survey in DB
    survey_id = await create_survey(callback.from_user.id, text, json.dumps(photos))

    await callback.message.edit_reply_markup(reply_markup=None)
    status_msg = await callback.message.answer(f"🚀 Починаю розсилку опитування на {len(target_groups)} груп...")
    
    success_count = 0
    kb = get_survey_action_kb(survey_id)
    
    for group_id in target_groups:
        try:
            sent_ids = []
            if photos:
                if len(photos) == 1:
                    sent = await bot.send_photo(chat_id=group_id, photo=photos[0], caption=text, reply_markup=kb, parse_mode="HTML")
                    sent_ids.append(sent.message_id)
                else:
                    media = [InputMediaPhoto(media=p) for p in photos]
                    media[0].caption = text
                    media[0].parse_mode = "HTML"
                    sent_msgs = await bot.send_media_group(chat_id=group_id, media=media)
                    sent_ids = [m.message_id for m in sent_msgs]
                    # Since MediaGroup doesn't support reply_markup, we send a separate message with buttons
                    sent_btn = await bot.send_message(chat_id=group_id, text="👇 Дайте відповідь на питання вище:", reply_markup=kb)
                    sent_ids.append(sent_btn.message_id)
            else:
                sent = await bot.send_message(chat_id=group_id, text=text, reply_markup=kb, parse_mode="HTML")
                sent_ids.append(sent.message_id)
            
            await add_survey_message(survey_id, group_id, json.dumps(sent_ids))
            success_count += 1
            await asyncio.sleep(0.2)
        except Exception as e:
            logger.error(f"Failed to send survey to {group_id}: {e}")

    await status_msg.edit_text(
        f"✅ <b>Опитування відправлено!</b>\nУспішно: {success_count}/{len(target_groups)}", 
        parse_mode="HTML"
    )
    # Restore the main menu for admin
    await callback.message.answer("Керування завершено.", reply_markup=get_admin_main_keyboard())
    await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("survey_archive:"))
async def view_survey_archive(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    per_page = config.users_per_page
    
    total_count = await count_surveys()
    surveys = await get_all_surveys(limit=per_page, offset=page * per_page)
    
    total_pages = (total_count + per_page - 1) // per_page
    
    text = f"📂 <b>Архів опитувань</b> (Всього: {total_count})"
    if not surveys:
        text = "📂 Архів порожній."
        
    await callback.message.edit_text(
        text, 
        reply_markup=get_survey_archive_kb(surveys, page, total_pages),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("survey_view:"))
async def view_single_survey(callback: CallbackQuery):
    survey_id = int(callback.data.split(":")[1])
    survey = await get_survey(survey_id)
    if not survey:
        await callback.answer("Опитування не знайдено.", show_alert=True)
        return
        
    msgs = await get_survey_messages(survey_id)
    responses = await get_survey_responses(survey_id)
    
    text = f"📄 <b>Деталі опитування #{survey_id}</b>\n"
    text += f"📅 Дата: {survey['created_at']}\n"
    text += f"👥 Груп: {len(msgs)}\n"
    text += f"📥 Відповідей: {len(responses)}\n\n"
    text += f"📝 <b>Текст:</b>\n{survey['text'] or '[Без тексту]'}"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_survey_manage_kb(survey_id),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("survey_results:"))
async def view_survey_results(callback: CallbackQuery):
    survey_id = int(callback.data.split(":")[1])
    responses = await get_survey_responses(survey_id)
    
    if not responses:
        await callback.answer("Відповідей ще немає.", show_alert=True)
        return
        
    text = f"📊 <b>Результати опитування #{survey_id}:</b>\n\n"
    for r in responses[:15]: # Show last 15
        ans_icon = "✅" if r['answer'] == "yes" else "❌"
        text += f"{ans_icon} {r['tc_name']} | {r['full_name']}\n"
        if r['comment']:
            text += f"  └ 💬 {r['comment']}\n"
    
    if len(responses) > 15:
        text += f"\n... та ще {len(responses)-15} відповідей."
        
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("survey_delete:"))
async def process_survey_delete(callback: CallbackQuery, bot: Bot):
    survey_id = int(callback.data.split(":")[1])
    
    msgs = await get_survey_messages(survey_id)
    await callback.answer("Видаляю опитування...")
    
    for m in msgs:
        try:
            msg_ids = json.loads(m['message_id'])
            for mid in msg_ids:
                try:
                    await bot.delete_message(chat_id=m['chat_id'], message_id=mid)
                except: pass
            await asyncio.sleep(0.05)
        except: pass
        
    await delete_survey_from_db(survey_id)
    await view_survey_archive(callback)
