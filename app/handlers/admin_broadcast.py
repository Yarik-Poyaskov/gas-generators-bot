import asyncio
import logging
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
    get_all_broadcasts, count_broadcasts
)
from app.keyboards.inline import (
    get_broadcast_main_kb, get_broadcast_preview_kb, 
    get_broadcast_archive_kb, get_broadcast_manage_kb
)
from app.keyboards.reply import get_admin_main_keyboard, get_simple_cancel_kb
from app.states.admin import BroadcastState

logger = logging.getLogger(__name__)
router = Router()
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
        "Коли будете готові, бот покаже предпросмотр.",
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
    
    await message.answer("👀 <b>Предпросмотр розсилки:</b>", reply_markup=get_admin_main_keyboard(), parse_mode="HTML")
    
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
