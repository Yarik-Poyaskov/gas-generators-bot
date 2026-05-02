import json
import logging
import asyncio
import re
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo
from aiogram import Bot

from app.config import config
from app.db.database import (
    get_schedules_for_report, 
    check_report_exists, 
    was_reminder_sent, 
    log_sent_reminder,
    get_setting,
    get_required_objects,
    get_active_shift_on_object,
    get_reports_by_date
)

logger = logging.getLogger(__name__)
KYIV_TZ = ZoneInfo("Europe/Kiev")

async def check_mandatory_checklists(bot: Bot):
    """
    Checks if all mandatory objects have submitted at least one report today.
    If not, sends an alert to the object's group.
    """
    now_kyiv = datetime.now(KYIV_TZ)
    today_db = now_kyiv.strftime("%Y-%m-%d")
    
    # 1. Get all mandatory objects
    req_objects = await get_required_objects()
    if not req_objects:
        return

    # 2. Get all reports for today
    today_reports = await get_reports_by_date(today_db)
    
    # Create a set of object names that HAVE reports today
    reported_objects = set()
    for r in today_reports:
        # Extract name part inside parentheses if exists
        name = r['tc_name']
        reported_objects.add(name)
        # Also try to match by short name or partial name to be safe
        match = re.search(r'\((.*?)\)', name)
        if match:
            reported_objects.add(match.group(1))

    for obj in req_objects:
        group_id = obj['telegram_group_id']
        if not group_id:
            continue
            
        # Check if this object has any report today
        obj_name = obj['name']
        short_name = obj_name
        match = re.search(r'\((.*?)\)', obj_name)
        if match:
            short_name = match.group(1)
            
        has_report = False
        for rep_name in reported_objects:
            if short_name in rep_name or obj_name in rep_name:
                has_report = True
                break
        
        if not has_report:
            # Report is MISSING!
            # 3. Check for active shift
            shift = await get_active_shift_on_object(obj['id'])
            
            if shift:
                mention = f"<b>{shift['full_name']}</b>"
                msg = f"⚠️ {mention}, Ви не подали Чек Лист!"
            else:
                msg = "⚠️ Ви не подали Чек Лист!"
                
            try:
                await bot.send_message(chat_id=group_id, text=msg, parse_mode="HTML")
                logger.info(f"Sent mandatory checklist alert for {obj_name}")
            except Exception as e:
                logger.error(f"Failed to send alert to group {group_id}: {e}")

async def check_and_send_report_reminders(bot: Bot):
    """
    Checks all schedules for today and sends reminders to groups 
     if the report (start/stop) is missing after the margin.
    """
    # 1. Get margin from settings (default 20 mins)
    margin_str = await get_setting('report_reminder_margin', '20')
    try:
        margin_mins = int(margin_str)
    except:
        margin_mins = 20

    # 2. Get current time in Kyiv
    now_kyiv = datetime.now(KYIV_TZ)
    today_db = now_kyiv.strftime("%Y-%m-%d")
    
    # 3. Fetch all schedules for today
    # get_schedules_for_report returns objects even without schedule, but with schedule_id if exists
    schedules = await get_schedules_for_report(today_db)
    
    for s in schedules:
        # We only care about objects that HAVE a schedule today and aren't marked as 'is_not_working'
        if not s.get('schedule_id') or s.get('is_not_working'):
            continue
            
        group_id = s.get('telegram_group_id')
        if not group_id:
            continue

        # Fetch full schedule data to get intervals
        from app.db.database import get_schedule_by_id
        full_schedule = await get_schedule_by_id(s['schedule_id'])
        if not full_schedule or not full_schedule.get('schedule_json'):
            continue
            
        try:
            intervals = json.loads(full_schedule['schedule_json'])
        except:
            continue

        obj_name = s['tc_name']
        
        for interval in intervals:
            start_time_str = interval.get('start')
            end_time_str = interval.get('end')
            
            # Check Start Reminder
            if start_time_str:
                await process_event_reminder(
                    bot, s['schedule_id'], group_id, obj_name, 
                    start_time_str, 'start', margin_mins, now_kyiv, today_db
                )
            
            # Check Stop Reminder
            if end_time_str:
                await process_event_reminder(
                    bot, s['schedule_id'], group_id, obj_name, 
                    end_time_str, 'stop', margin_mins, now_kyiv, today_db
                )

async def process_event_reminder(bot, schedule_id, group_id, obj_name, event_time_str, event_type, margin, now_kyiv, today_db):
    """Checks and sends a specific reminder for a start or stop event."""
    try:
        # Parse event time (HH:MM)
        event_h, event_m = map(int, event_time_str.split(':'))
        event_dt = now_kyiv.replace(hour=event_h, minute=event_m, second=0, microsecond=0)
        
        # We only remind if Event_Time + Margin has passed, but not more than 2 hours ago (to avoid spamming old events)
        reminder_threshold = event_dt + timedelta(minutes=margin)
        expiration_threshold = event_dt + timedelta(hours=2)

        if reminder_threshold <= now_kyiv <= expiration_threshold:
            # Check if reminder already sent
            if await was_reminder_sent(schedule_id, event_type, event_time_str):
                return

            # CONVERT event time to UTC for DB search
            # (Assuming +3h offset for Kyiv)
            event_utc = event_dt - timedelta(hours=3)

            # Check if report already exists in DB (around or after event time)
            if await check_report_exists(obj_name, event_type, event_utc):
                return

            # If we are here - report is missing!
            action = "ЗАПУЩЕНА" if event_type == 'start' else "ЗУПИНЕНА"
            msg = (
                f"⚠️ <b>НАГАДУВАННЯ: ВІДСУТНІЙ ЗВІТ</b>\n\n"
                f"Згідно з графіком, ГПУ <b>{obj_name}</b> мала бути <b>{action}</b> о <b>{event_time_str}</b>.\n"
                f"Минуло вже {margin} хвилин, але звіт «Статус ГПУ» ще не подано.\n\n"
                f"☝️ Будь ласка, заповніть статус у боті!"
            )
            
            try:
                await bot.send_message(chat_id=group_id, text=msg, parse_mode="HTML")
                await log_sent_reminder(schedule_id, event_type, event_time_str)
                logger.info(f"Sent {event_type} reminder for {obj_name} (scheduled {event_time_str})")
            except Exception as e:
                logger.error(f"Failed to send reminder to {group_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error processing {event_type} reminder for {obj_name}: {e}")
