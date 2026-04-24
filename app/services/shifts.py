import logging
import aiosqlite
from datetime import datetime, timedelta
from aiogram import Bot
from app.db.database import DB_PATH, get_setting, get_object_by_id, get_user

async def auto_close_shifts_task(bot: Bot):
    """
    Background task to automatically close shifts if enabled.
    Rules (from Project Logic):
    1. Close if 'planned_end_time' (local) is reached (with a grace period to allow reminder to work).
    2. If a NEWER shift exists on the same object, close the OLD one only if 2 hours passed since the NEW shift started 
       AND the old one still hasn't set a planned_end_time (didn't reply to handover question).
    3. Close if the shift is older than 24 hours (safety measure).
    """
    is_auto_close_enabled = await get_setting('auto_close_shifts', '0') == '1'
    if not is_auto_close_enabled:
        return

    now_local = datetime.now()
    now_utc = datetime.utcnow()
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Get all active shifts
        cursor = await db.execute("SELECT * FROM shifts WHERE end_time IS NULL")
        all_active_shifts = await cursor.fetchall()
        
        # Organize shifts by object to detect handovers
        shifts_by_object = {}
        for shift in all_active_shifts:
            obj_id = shift['object_id']
            if obj_id not in shifts_by_object:
                shifts_by_object[obj_id] = []
            shifts_by_object[obj_id].append(shift)

        for obj_id, shifts in shifts_by_object.items():
            shifts.sort(key=lambda x: x['start_time'], reverse=True)
            
            newest_shift_start_str = shifts[0]['start_time']
            try:
                newest_start_dt = datetime.strptime(newest_shift_start_str, "%Y-%m-%d %H:%M:%S")
            except:
                newest_start_dt = now_utc

            for i, shift in enumerate(shifts):
                if i == 0: continue
                
                reason = None
                
                # Rule 1: Planned end time reached (local time)
                # Give a 15-minute grace period so the reminder has time to be seen
                if shift['planned_end_time']:
                    try:
                        planned_dt = datetime.strptime(shift['planned_end_time'], "%Y-%m-%d %H:%M:%S")
                        if now_local >= (planned_dt + timedelta(minutes=15)):
                            reason = "плановий час закінчення (+15хв)"
                    except Exception as e:
                        logging.error(f"Error parsing planned_end_time for shift {shift['id']}: {e}")

                # Rule 2: Handover logic
                if not reason and not shift['planned_end_time']:
                    if (now_utc - newest_start_dt) > timedelta(hours=2):
                        reason = "немає відповіді на запит передачі зміни (>2г)"

                # Rule 3: General safety
                if not reason:
                    try:
                        start_dt = datetime.strptime(shift['start_time'], "%Y-%m-%d %H:%M:%S")
                        if (now_utc - start_dt) > timedelta(hours=24):
                            reason = "перевищено ліміт 24 години"
                    except Exception as e:
                        logging.error(f"Error parsing start_time for shift {shift['id']}: {e}")

                if reason:
                    await db.execute(
                        "UPDATE shifts SET end_time = CURRENT_TIMESTAMP, auto_closed = 1 WHERE id = ?",
                        (shift['id'],)
                    )
                    await db.commit()
                    
                    obj = await get_object_by_id(shift['object_id'])
                    user = await get_user(shift['user_id'])
                    user_name = user['full_name'] if user else "Співробітник"
                    
                    if obj and obj.get('telegram_group_id'):
                        msg = (
                            f"⚠️ Зміна <b>{user_name}</b> закрита автоматично ({reason}).\n"
                            f"<b>{user_name}</b> - будьте уважні та своєчасно закривайте свою зміну."
                        )
                        try:
                            await bot.send_message(chat_id=obj['telegram_group_id'], text=msg, parse_mode="HTML")
                        except Exception as e:
                            logging.error(f"Failed to send auto-close notification to group: {e}")
                    
                    logging.info(f"Shift {shift['id']} for user {shift['user_id']} was auto-closed. Reason: {reason}")

async def send_shift_reminders_task(bot: Bot):
    """
    Checks for shifts that reached their planned_end_time and sends a private message reminder.
    Runs every minute.
    """
    now_local = datetime.now()
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Find active shifts with planned_end_time that haven't received a reminder yet
        cursor = await db.execute(
            "SELECT * FROM shifts WHERE end_time IS NULL AND planned_end_time IS NOT NULL AND reminder_sent = 0 AND planned_end_time <= ?",
            (now_local.strftime("%Y-%m-%d %H:%M:%S"),)
        )
        to_remind = await cursor.fetchall()
        
        for shift in to_remind:
            obj = await get_object_by_id(shift['object_id'])
            obj_name = obj['name'] if obj else "Об'єкт"
            
            msg = (
                f"🔔 <b>Нагадування про закінчення зміни!</b>\n\n"
                f"Ваша запланована зміна на об'єкті <b>{obj_name}</b> мала закінчитись о {shift['planned_end_time'].split(' ')[1][:5]}.\n\n"
                f"Будь ласка, закрийте зміну через меню 👤 <b>Керування змінами</b>, якщо ви вже закінчили роботу."
            )
            
            try:
                await bot.send_message(chat_id=shift['user_id'], text=msg, parse_mode="HTML")
                # Mark as sent
                await db.execute("UPDATE shifts SET reminder_sent = 1 WHERE id = ?", (shift['id'],))
                await db.commit()
                logging.info(f"Sent shift end reminder to user {shift['user_id']} for shift {shift['id']}")
            except Exception as e:
                logging.error(f"Failed to send shift reminder to user {shift['user_id']}: {e}")
