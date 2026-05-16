import json
import re
import logging
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from app.config import config
from app.db.database import (
    get_all_objects, add_trader_schedule, get_user,
    add_trader_announcement, get_trader_announcements,
    delete_trader_announcements_from_db, delete_schedules_by_date
)
from app.keyboards.inline import (
    get_parser_edit_objects_kb, get_parser_edit_field_kb, get_schedule_confirm_kb
)
from app.states.trader import TraderParserState

logger = logging.getLogger(__name__)
router = Router()

MAPPING_FILE = "mapping.json"

def load_mapping():
    try:
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading mapping.json: {e}")
        return {}

def normalize_text(text: str) -> str:
    """Replaces common look-alike Latin characters with Cyrillic and converts to uppercase."""
    if not text: return ""
    trans = str.maketrans("KCAXOPMEIT", "КСАХОРМЕІТ")
    return text.upper().translate(trans)

def parse_trader_message(text: str, mapping: dict):
    """Parses trader's message and returns structured data with GPU-specific handling."""
    is_correction = "коригування" in text.lower()
    
    # 1. Extract Date
    date_match = re.search(r"(\d{2}[/.]\d{2}[/.]\d{4})", text)
    if not date_match:
        return None, "Не знайдено дату в повідомленні."
    
    target_date_raw = date_match.group(1).replace(".", "/")
    try:
        target_date = datetime.strptime(target_date_raw, "%d/%m/%Y").strftime("%Y-%m-%d")
    except:
        return None, "Некоректний формат дати."

    # 2. Split text into object blocks
    if re.search(r"(?im)^По\s+", text):
        blocks = re.split(r"(?im)^По\s+", text)
        if not blocks[0].lower().strip().startswith("по "):
            blocks = blocks[1:]
    else:
        blocks = re.split(r"\n\n|\n(?=\")", text)
        blocks = [b.strip() for b in blocks if b.strip() and "графік роботи на" not in b.lower() and "коригування на" not in b.lower()]

    results = []
    for block in blocks:
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines: continue
        
        header_line = lines[0].replace('"', '').strip()
        object_header = header_line.split(":")[0].strip()
        norm_header = normalize_text(object_header)
        
        matched_db_names = []
        for key, db_names in mapping.items():
            norm_key = normalize_text(key)
            if re.search(rf"(?<!\w){re.escape(norm_key)}(?!\w)", norm_header, re.IGNORECASE):
                matched_db_names = db_names
                break
        
        if not matched_db_names:
            for key, db_names in mapping.items():
                for db_name in db_names:
                    clean_db_name = re.sub(r"[\(\)]", "", db_name)
                    norm_db_name = normalize_text(clean_db_name)
                    if norm_db_name in norm_header:
                        matched_db_names = [db_name]
                        break
                if matched_db_names: break
        
        if not matched_db_names: continue

        gpu_intervals = {i: [] for i in range(len(matched_db_names) + 1)}
        # Блок считается нерабочим только если в заголовке есть " - " или ":-" или он заканчивается на "-"
        # И при этом в блоке нет найденных интервалов времени.
        block_is_not_working = (
            re.search(r"[:\s]-$|:-\s| - ", header_line) is not None and 
            (len(lines) == 1 or "режим" not in block.lower())
        )

        for line in lines:
            # Handle correction format: "режим острів до 22-00"
            if is_correction and "режим" in line.lower():
                mode = "Острів" if "острів" in line.lower() else "Мережа"
                time_to_match = re.search(r"(?:до|по)\s*(\d{1,2}[:.-]\d{2})", line.lower())
                time_from_match = re.search(r"(?:з|от)\s*(\d{1,2}[:.-]\d{2})", line.lower())
                
                start = time_from_match.group(1).replace("-", ":").replace(".", ":") if time_from_match else "00:00"
                end = time_to_match.group(1).replace("-", ":").replace(".", ":") if time_to_match else "24:00"
                
                if len(start.split(":")[0]) == 1: start = "0" + start
                if len(end.split(":")[0]) == 1: end = "0" + end
                
                gpu_intervals[0].append({"start": start, "end": end, "power": 100, "mode": mode})
                block_is_not_working = False
                continue

            # Standard interval matching "з 08:00 до 12:00"
            time_matches = re.findall(r"(?i)з\s*(\d{1,2}[:.-]\d{2})\s*(?:до|по|–|-)\s*(\d{1,2}[:.-]\d{2})", line)
            if not time_matches: continue
                
            gpu_mention_match = re.search(r"(?i)(?:GPU|ГПУ)[-\s]*(\d+)|(\d+)\s*ГПУ", line)
            gpu_idx = int(gpu_mention_match.group(1) or gpu_mention_match.group(2)) if gpu_mention_match else 0
            
            power_match = re.search(r"(\d{1,3})%", line)
            power = int(power_match.group(1)) if power_match else 100
            mode = "Острів" if "острів" in line.lower() else "Мережа"

            for start, end in time_matches:
                start, end = start.replace("-", ":").replace(".", ":"), end.replace("-", ":").replace(".", ":")
                if len(start.split(":")[0]) == 1: start = "0" + start
                if len(end.split(":")[0]) == 1: end = "0" + end
                
                interval = {"start": start, "end": end, "power": power, "mode": mode}
                if gpu_idx <= len(matched_db_names):
                    gpu_intervals[gpu_idx].append(interval)

        for i, db_name in enumerate(matched_db_names, 1):
            final_intervals = gpu_intervals[0] + gpu_intervals[i]
            final_intervals.sort(key=lambda x: x['start'])
            
            # Если найдены интервалы, объект точно работает
            is_really_not_working = block_is_not_working
            if final_intervals:
                is_really_not_working = False
            elif not is_correction:
                is_really_not_working = True
                
            results.append({
                "db_name": db_name,
                "target_date": target_date,
                "intervals": final_intervals,
                "is_not_working": is_really_not_working
            })

    return results, target_date_raw

def format_review_text(parsed_data, date_str, is_editing=False):
    """Formats the structured data for display."""
    title = "🤖 <b>Режим редагування графіка</b>" if is_editing else "🤖 <b>Розпізнано графік</b>"
    if "коригування" in title.lower(): # This won't work easily here, let's adjust caller
        pass 
    text = f"{title} на {date_str}\n\n"
    for item in parsed_data:
        display_name = re.sub(r"[\(\)]", "", item['db_name'])
        if item['is_not_working']:
            status = "❌ Не працює"
        else:
            intervals_str = [f"{inv['start']}-{inv['end']} ({inv['power']}%, {inv['mode'].lower()})" for inv in item['intervals']]
            status = "✅ " + "; ".join(intervals_str)
        text += f"🏢 <b>{display_name}</b>: {status}\n"
    return text

@router.message(F.chat.id == config.trader_monitor_group_id)
async def handle_trader_group_message(message: Message, state: FSMContext):
    if not message.text: return
    
    msg_lower = message.text.strip().lower()
    is_sched = msg_lower.startswith("графік роботи на")
    is_corr = msg_lower.startswith("коригування на")
    
    if not (is_sched or is_corr):
        return

    if message.from_user.id not in config.monitored_trader_ids:
        return

    mapping = load_mapping()
    parsed_data, date_str = parse_trader_message(message.text, mapping)
    if not parsed_data: return

    user_data = await get_user(message.from_user.id)
    trader_name = user_data['full_name'] if user_data else message.from_user.full_name

    title = "⚙️ <b>КОРИГУВАННЯ ГРАФІКА</b>" if is_corr else "🤖 <b>Розпізнано графік</b>"
    text = f"Вітаю, <b>{trader_name}</b>! {title}:\n\n"
    # Extract only the body of the formatted review
    review_body = format_review_text(parsed_data, date_str).split('\n\n', 1)[1]
    text += review_body
    text += "\n<b>Оновити дані в базі?</b>"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Підтвердити", callback_data="trader_parse_confirm"),
            InlineKeyboardButton(text="✏️ Редагувати", callback_data="trader_parse_edit")
        ],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="trader_parse_cancel")]
    ])
    
    sent_msg = await message.reply(text, reply_markup=kb, parse_mode="HTML")
    
    # Save group info to state
    await state.update_data(
        parsed_trader_data=parsed_data, 
        trader_id=message.from_user.id, 
        date_str=date_str,
        group_chat_id=message.chat.id,
        group_message_id=sent_msg.message_id,
        trader_name=trader_name,
        is_correction=is_corr
    )
    await state.set_state(TraderParserState.reviewing)

@router.callback_query(TraderParserState.reviewing, F.data == "trader_parse_edit")
async def enter_edit_mode(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    trader_id = callback.from_user.id
    
    try:
        # Try to send message to PM
        review_text = format_review_text(data['parsed_trader_data'], data['date_str'], is_editing=True)
        review_text += "\nОберіть об'єкт для коригування:"
        
        await bot.send_message(
            chat_id=trader_id, 
            text=review_text, 
            reply_markup=get_parser_edit_objects_kb(data['parsed_trader_data']),
            parse_mode="HTML"
        )
        
        # Update group message
        await callback.message.edit_text(
            f"🛠 <b>{data.get('trader_name')}</b> редагує цей графік в особистих повідомленнях...",
            reply_markup=None, parse_mode="HTML"
        )
        await state.set_state(TraderParserState.selecting_obj)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Failed to send PM to trader {trader_id}: {e}")
        await callback.answer(
            "⚠️ Не можу написати вам у приватні повідомлення! Будь ласка, натисніть /start у боті та спробуйте ще раз.",
            show_alert=True
        )

# --- Private Editing Handlers ---

async def update_private_review(message: Message, state: FSMContext):
    data = await state.get_data()
    review_text = format_review_text(data['parsed_trader_data'], data['date_str'], is_editing=True)
    review_text += "\nОберіть об'єкт для коригування:"
    await message.edit_text(review_text, reply_markup=get_parser_edit_objects_kb(data['parsed_trader_data']), parse_mode="HTML")

@router.callback_query(TraderParserState.selecting_obj, F.data.startswith("pedit_obj:"))
async def select_obj_to_edit(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    item = data['parsed_trader_data'][idx]
    display_name = re.sub(r"[\(\)]", "", item['db_name'])
    
    await state.update_data(editing_idx=idx)
    await state.set_state(TraderParserState.editing_obj)
    await callback.message.edit_text(
        f"⚙️ <b>Коригування: {display_name}</b>\n\nОберіть що змінити:", 
        reply_markup=get_parser_edit_field_kb(idx, item), 
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(TraderParserState.editing_obj, F.data == "pedit_back_list")
async def back_to_list(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TraderParserState.selecting_obj)
    await update_private_review(callback.message, state)
    await callback.answer()

@router.callback_query(TraderParserState.editing_obj, F.data.startswith("pedit_toggle_work:"))
async def toggle_work(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    parsed_data = list(data['parsed_trader_data'])
    item = parsed_data[idx]
    item['is_not_working'] = not item['is_not_working']
    if not item['is_not_working'] and not item['intervals']:
        item['intervals'] = [{"start": "00:00", "end": "24:00", "power": 100, "mode": "Мережа"}]
    await state.update_data(parsed_trader_data=parsed_data)
    await callback.message.edit_reply_markup(reply_markup=get_parser_edit_field_kb(idx, item))
    await callback.answer()

@router.callback_query(TraderParserState.editing_obj, F.data.startswith("pedit_cycle_pwr:"))
async def cycle_power(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    parsed_data = list(data['parsed_trader_data'])
    item = parsed_data[idx]
    if item['intervals']:
        powers = [100, 70, 50, 0]
        curr = int(item['intervals'][0]['power'])
        nxt = powers[(powers.index(curr) + 1) % len(powers)] if curr in powers else 100
        for inv in item['intervals']: inv['power'] = nxt
    await state.update_data(parsed_trader_data=parsed_data)
    await callback.message.edit_reply_markup(reply_markup=get_parser_edit_field_kb(idx, item))
    await callback.answer()

@router.callback_query(TraderParserState.editing_obj, F.data.startswith("pedit_cycle_mode:"))
async def cycle_mode(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    parsed_data = list(data['parsed_trader_data'])
    item = parsed_data[idx]
    if item['intervals']:
        nxt = "Острів" if item['intervals'][0]['mode'] == "Мережа" else "Мережа"
        for inv in item['intervals']: inv['mode'] = nxt
    await state.update_data(parsed_trader_data=parsed_data)
    await callback.message.edit_reply_markup(reply_markup=get_parser_edit_field_kb(idx, item))
    await callback.answer()

@router.callback_query(TraderParserState.editing_obj, F.data.startswith("pedit_input_time:"))
async def start_time_input(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TraderParserState.input_time)
    # Using a new message instead of editing to allow text input
    await callback.message.answer("🕒 Введіть інтервали (напр: <code>08:00-12:00, 14:00-22:00</code>):", parse_mode="HTML")
    await callback.answer()

@router.message(TraderParserState.input_time)
async def process_manual_time(message: Message, state: FSMContext, bot: Bot):
    if not message.text:
        await message.answer("⚠️ Будь ласка, введіть інтервали <b>текстом</b>.")
        return
        
    data = await state.get_data()
    idx = data['editing_idx']
    parsed_data = list(data['parsed_trader_data'])
    item = parsed_data[idx]
    
    matches = re.findall(r"(\d{1,2}[:.]\d{2})\s*-\s*(\d{1,2}[:.]\d{2})", message.text)
    if not matches:
        await message.answer("❌ Некоректний формат. Спробуйте: 07:00-10:00")
        return

    base_pwr = item['intervals'][0]['power'] if item['intervals'] else 100
    base_mode = item['intervals'][0]['mode'] if item['intervals'] else "Мережа"
    new_inv = []
    for s, e in matches:
        s, e = s.replace(".", ":"), e.replace(".", ":")
        if len(s.split(":")[0]) == 1: s = "0" + s
        if len(e.split(":")[0]) == 1: e = "0" + e
        new_inv.append({"start": s, "end": e, "power": base_pwr, "mode": base_mode})

    item['intervals'] = sorted(new_inv, key=lambda x: x['start'])
    item['is_not_working'] = False
    await state.update_data(parsed_trader_data=parsed_data)
    await state.set_state(TraderParserState.selecting_obj)
    
    # Send a NEW menu message after text input
    review_text = format_review_text(parsed_data, data['date_str'], is_editing=True)
    await message.answer(review_text + "\nОберіть об'єкт:", reply_markup=get_parser_edit_objects_kb(parsed_data), parse_mode="HTML")

# --- Fallbacks ---

@router.message(TraderParserState.reviewing)
@router.message(TraderParserState.selecting_obj)
@router.message(TraderParserState.editing_obj)
@router.message(TraderParserState.confirm_revoke)
async def handle_parser_inline_kb_fallbacks(message: Message, state: FSMContext):
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
            from app.handlers.trader import cmd_trader_schedule_start
            return await cmd_trader_schedule_start(message, state)
        elif message.text == "Відміна":
            from app.handlers.report import cmd_cancel_report
            return await cmd_cancel_report(message, state)

    await message.answer("⚠️ Будь ласка, використовуйте <b>кнопки</b> під повідомленням.")


# --- Confirm / Cancel (Works from both Group and PM) ---

@router.callback_query(F.data == "trader_parse_confirm")
async def confirm_parsed_schedule(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    parsed_items = data.get("parsed_trader_data")
    if not parsed_items:
        await callback.answer("Дані застаріли.", show_alert=True)
        return

    all_objs = await get_all_objects()
    obj_map = {o['name']: (o['id'], o['telegram_group_id']) for o in all_objs}

    success_count = 0
    target_date = ""
    for item in parsed_items:
        target_date = item['target_date']
        obj_info = next((info for name, info in obj_map.items() if item['db_name'] in name), None)
        if obj_info:
            obj_id, group_id = obj_info
            sched_id = await add_trader_schedule(obj_id, data['trader_id'], item['target_date'], json.dumps(item['intervals'], ensure_ascii=False), item['is_not_working'])
            success_count += 1
            if group_id:
                try:
                    date_disp = datetime.strptime(item['target_date'], "%Y-%m-%d").strftime("%d.%m.%Y")
                    msg = f"📅 <b>ГРАФІК РОБОТИ: {date_disp}</b>\n🏢 Об'єкт: <b>{item['db_name']}</b>\n\n"
                    msg += "❌ <b>ГПУ НЕ ПРАЦЮЄ</b>" if item['is_not_working'] else "\n".join([f"• {i['start']} - {i['end']} | {i['power']}% | {i['mode']}" for i in item['intervals']])
                    sent_announcement = await bot.send_message(
                        chat_id=group_id, 
                        text=msg + "\n\n👉 Підтвердіть графік.", 
                        reply_markup=get_schedule_confirm_kb(sched_id), 
                        parse_mode="HTML"
                    )
                    # Track announcement for revoking
                    await add_trader_announcement(
                        trader_id=data['trader_id'], 
                        target_date=item['target_date'], 
                        chat_id=group_id, 
                        message_id=sent_announcement.message_id,
                        object_id=obj_id,
                        message_type='announcement'
                    )
                except Exception as e:
                    logger.error(f"Failed to send announcement to group {group_id}: {e}")

    # Update original group message
    final_text = format_review_text(parsed_items, data['date_str']) + f"\n✅ <b>Збережено в базу!</b> ({success_count} об'єктів)\n🚀 <b>Надіслано до всіх груп</b>"
    
    # Add Revoke button
    revoke_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Відкликати графік", callback_data=f"revoke_sched:{target_date}")]
    ])

    try:
        await bot.edit_message_text(
            chat_id=data['group_chat_id'], 
            message_id=data['group_message_id'], 
            text=final_text, 
            reply_markup=revoke_kb,
            parse_mode="HTML"
        )
    except: pass

    await state.clear()
    if callback.message.chat.type == "private":
        await callback.message.edit_text("✅ Графік успішно збережено та відправлено в групи!")
    await callback.answer()

@router.callback_query(F.data == "trader_parse_cancel")
async def cancel_parsed_schedule(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    if not data or 'parsed_trader_data' not in data:
        await callback.answer("Дані застаріли.", show_alert=True)
        try:
            await callback.message.delete()
        except: pass
        await state.clear()
        return

    final_text = format_review_text(data['parsed_trader_data'], data['date_str']) + "\n❌ <b>Скасовано. Дані не збережені.</b>"
    try:
        await bot.edit_message_text(chat_id=data['group_chat_id'], message_id=data['group_message_id'], text=final_text, parse_mode="HTML")
    except: pass
    await state.clear()
    if callback.message.chat.type == "private":
        await callback.message.edit_text("❌ Скасовано.")
    await callback.answer()

# --- Revoke Schedule Logic ---

@router.callback_query(F.data.startswith("revoke_sched:"))
async def ask_revoke_confirmation(callback: CallbackQuery, state: FSMContext):
    target_date = callback.data.split(":")[1]
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Так, відкликати", callback_data=f"confirm_revoke:{target_date}"),
            InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_revoke")
        ]
    ])
    
    await callback.message.reply(
        "❓ <b>Ви впевнені, що хочете відкликати цей графік?</b>\n"
        "Всі повідомлення в групах об'єктів будуть видалені, а дані стерті з бази.",
        reply_markup=kb, parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_revoke:"))
async def process_revoke_schedule(callback: CallbackQuery, state: FSMContext, bot: Bot):
    target_date = callback.data.split(":")[1]
    trader_id = callback.from_user.id
    now_dt = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    
    # Get all messages sent to groups for this schedule
    announcements = await get_trader_announcements(trader_id, target_date)
    
    success_count = 0
    from app.db.database import get_object_by_id
    
    for ann in announcements:
        try:
            msg_type = ann.get('message_type', 'announcement')
            
            if msg_type == 'confirmation':
                # Edit confirmed message: ✅ -> ⚠️ and add "ANNULLED"
                obj = await get_object_by_id(ann['object_id'])
                display_name = re.sub(r"[\(\)]", "", obj['name']) if obj else "Об'єкт"
                
                # To reconstruct the message accurately, we can try to "guess" it or just append
                # Since we don't have the original confirmed user name easily here, 
                # we will try to EDIT it blind OR just send a NEW one.
                # Requirement says: "редактировать ЭТО сообщение"
                
                # We'll try to reconstruct based on the typical format
                annulled_text = (
                    f"⚠️ <b>ПОТОЧНИЙ ГРАФІК АНУЛЬОВАНО!!!</b>\n\n"
                    f"<b>Об'єкт:</b> {display_name}\n"
                    f"<b>На дату:</b> {target_date}\n"
                    f"🕒 <b>Час скасування:</b> {now_dt}\n\n"
                    f"❌ <b>ПОТОЧНИЙ ГРАФІК АНУЛЬОВАНО!!!</b>"
                )
                try:
                    await bot.edit_message_text(
                        chat_id=ann['chat_id'],
                        message_id=ann['message_id'],
                        text=annulled_text,
                        parse_mode="HTML"
                    )
                except:
                    # If edit fails, it might be already deleted or not editable
                    await bot.delete_message(chat_id=ann['chat_id'], message_id=ann['message_id'])
            else:
                # Announcement message (with button) - just delete
                await bot.delete_message(chat_id=ann['chat_id'], message_id=ann['message_id'])
            
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to handle revocation for message {ann['message_id']}: {e}")

    # Delete from DB
    await delete_trader_announcements_from_db(trader_id, target_date)
    await delete_schedules_by_date(trader_id, target_date)

    # Update the main message in TRADER group
    try:
        current_text = callback.message.text or ""
        now_dt = datetime.now().strftime("%H:%M:%S")
        
        # We form new text by removing old status lines and adding revocation info
        lines = current_text.split('\n')
        cleaned_lines = []
        for line in lines:
            if "Збережено в базу" in line or "Надіслано до всіх груп" in line:
                continue
            cleaned_lines.append(line)
        
        new_text = "\n".join(cleaned_lines).strip()
        new_text += f"\n\n⚠️ <b>ГРАФІК ВІДКЛИКАНО</b> ({now_dt})"
        
        await callback.message.edit_text(
            text=new_text,
            reply_markup=None, # Remove the revoke button
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Failed to edit main message: {e}")
        await callback.message.answer(f"⚠️ <b>Графік на {target_date} був анульований!</b> ({now_dt})", parse_mode="HTML")
    
    # Delete the "Are you sure?" confirmation prompt
    try:
        # Check if the message we are in is the "Are you sure?" message
        # In ask_revoke_confirmation we used callback.message.reply(...)
        # So the confirmation prompt is a NEW message.
        # But this callback is from that confirmation prompt.
        await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    except: pass
    
    await callback.answer("Графік відкликано", show_alert=True)

@router.callback_query(F.data == "cancel_revoke")
async def cancel_revoke(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer("Скасовано")
