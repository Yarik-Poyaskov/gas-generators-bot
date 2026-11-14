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
    get_reports_by_date,
    get_schedule_by_object_and_date # Добавляем импорт для проверки стыковки суток
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
        obj_id = s['object_id'] # Передаем ID объекта для проверки непрерывности
        
        # Фильтруем валидные интервалы с указанным временем начала и конца
        valid_intervals = []
        for inv in intervals:
            if isinstance(inv, dict) and inv.get('start') and inv.get('end'):
                valid_intervals.append(inv)
                
        if not valid_intervals:
            continue
            
        def time_to_mins(t_str):
            try:
                parts = str(t_str).strip().split(':')
                return int(parts[0]) * 60 + int(parts[1])
            except:
                return 0

        def clean_power_val(p):
            if p is None:
                return ""
            p_str = str(p).strip().replace('%', '')
            if p_str in ['Н/З', 'Н/з', 'н/з', 'skip', '—', '-']:
                return ""
            return p_str

        def clean_mode_val(m):
            if m is None:
                return ""
            m_str = str(m).strip()
            if m_str.lower() in ['н/з', 'skip', '—', '-']:
                return ""
            return m_str

        def format_power_disp(p):
            cleaned = clean_power_val(p)
            return f"{cleaned}%" if cleaned else str(p or "")

        # Сортируем интервалы по времени начала
        sorted_intervals = sorted(valid_intervals, key=lambda x: time_to_mins(x.get('start', '00:00')))
        
        events_to_process = []
        n_inv = len(sorted_intervals)
        
        for idx in range(n_inv):
            curr_inv = sorted_intervals[idx]
            curr_start = curr_inv.get('start', '').strip()
            curr_end = curr_inv.get('end', '').strip()
            
            # 1. Проверяем точку начала (curr_start)
            # Если это стык с предыдущим интервалом (end предыдущего == start текущего)
            if idx > 0 and time_to_mins(sorted_intervals[idx - 1].get('end', '')) == time_to_mins(curr_start):
                prev_inv = sorted_intervals[idx - 1]
                
                p_prev_clean = clean_power_val(prev_inv.get('power'))
                p_curr_clean = clean_power_val(curr_inv.get('power'))
                m_prev_clean = clean_mode_val(prev_inv.get('mode'))
                m_curr_clean = clean_mode_val(curr_inv.get('mode'))
                
                power_changed = bool(p_prev_clean and p_curr_clean and p_prev_clean != p_curr_clean)
                mode_changed = bool(m_prev_clean and m_curr_clean and m_prev_clean.lower() != m_curr_clean.lower())
                
                extra_info = {
                    "power_prev": format_power_disp(prev_inv.get('power')),
                    "power_curr": format_power_disp(curr_inv.get('power')),
                    "mode_prev": prev_inv.get('mode', '').strip(),
                    "mode_curr": curr_inv.get('mode', '').strip()
                }
                
                if power_changed and mode_changed:
                    events_to_process.append((curr_start, 'combined_change', extra_info))
                elif power_changed:
                    events_to_process.append((curr_start, 'power_change', extra_info))
                elif mode_changed:
                    events_to_process.append((curr_start, 'mode_change', extra_info))
                else:
                    # Мощность и режим не изменились - машина продолжает работу без изменений
                    pass
            else:
                # Начало работы (первый запуск за день или запуск после перерыва)
                events_to_process.append((curr_start, 'start', {}))
                
            # 2. Проверяем точку завершения (curr_end)
            # Если конец текущего интервала стыкуется с началом следующего интервала,
            # остановка НЕ происходит (машина продолжает работу в следующем интервале)
            if idx + 1 < n_inv and time_to_mins(curr_end) == time_to_mins(sorted_intervals[idx + 1].get('start', '')):
                pass
            else:
                # Остановка ГПУ (конец рабочего дня или начало перерыва)
                events_to_process.append((curr_end, 'stop', {}))
                
        # Обрабатываем все события для объекта
        for ev_time, ev_type, extra in events_to_process:
            if ev_time:
                await process_event_reminder(
                    bot, s['schedule_id'], group_id, obj_name, 
                    ev_time, ev_type, margin_mins, now_kyiv, today_db, obj_id,
                    extra_info=extra
                )

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def process_event_reminder(bot, schedule_id, group_id, obj_name, event_time_str, event_type, margin, now_kyiv, today_db, object_id, extra_info=None):
    """Checks and sends a specific reminder for a start, stop, or change event."""
    try:
        # --- ЛОГИКА ПРОВЕРКИ НЕПРЕРЫВНОСТИ (СТЫК СУТОК) ---
        
        # 1. Если ЗАПУСК в 00:00 - проверяем, не работала ли машина вчера до 24:00
        if event_type == 'start' and event_time_str in ['00:00', '00:05']:
            yesterday_db = (now_kyiv - timedelta(days=1)).strftime("%Y-%m-%d")
            yesterday_sched = await get_schedule_by_object_and_date(object_id, yesterday_db)
            
            if yesterday_sched and not yesterday_sched.get('is_not_working'):
                try:
                    y_intervals = json.loads(yesterday_sched['schedule_json'])
                    is_continuation = False
                    for inv in y_intervals:
                        if inv.get('end') in ['24:00', '00:00', '23:59']:
                            is_continuation = True
                            break
                    
                    if is_continuation:
                        logger.info(f"Skipping midnight start reminder for {obj_name} (continuation from yesterday)")
                        return
                except:
                    pass

        # 2. Если ОСТАНОВКА в 24:00 - проверяем, не работает ли машина завтра с 00:00
        if event_type == 'stop' and event_time_str in ['24:00', '00:00', '23:59']:
            tomorrow_db = (now_kyiv + timedelta(days=1)).strftime("%Y-%m-%d")
            tomorrow_sched = await get_schedule_by_object_and_date(object_id, tomorrow_db)
            
            if tomorrow_sched and not tomorrow_sched.get('is_not_working'):
                try:
                    t_intervals = json.loads(tomorrow_sched['schedule_json'])
                    is_continuation = False
                    for inv in t_intervals:
                        if inv.get('start') in ['00:00', '00:05']:
                            is_continuation = True
                            break
                            
                    if is_continuation:
                        logger.info(f"Skipping midnight stop reminder for {obj_name} (continuation to tomorrow)")
                        return
                except:
                    pass
        # --------------------------------------------------

        # Parse event time (HH:MM)
        event_h, event_m = map(int, event_time_str.split(':'))
        
        # Handle 24:00 correctly for datetime (Python supports 0..23)
        if event_h == 24:
            # 24:00 is 00:00 of the NEXT day
            event_dt = (now_kyiv + timedelta(days=1)).replace(hour=0, minute=event_m, second=0, microsecond=0)
        else:
            event_dt = now_kyiv.replace(hour=event_h, minute=event_m, second=0, microsecond=0)
        
        # We only remind if Event_Time + Margin has passed, but not more than 2 hours ago (to avoid spamming old events)
        reminder_threshold = event_dt + timedelta(minutes=margin)
        expiration_threshold = event_dt + timedelta(hours=2)

        if reminder_threshold <= now_kyiv <= expiration_threshold:
            # Check if reminder already sent
            if await was_reminder_sent(schedule_id, event_type, event_time_str):
                return

            # CONVERT event time to UTC for DB search
            # Automatically handle timezone offset (Kyiv is UTC+2 in winter, UTC+3 in summer)
            if hasattr(event_dt, 'tzinfo') and event_dt.tzinfo:
                event_utc = event_dt.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                event_utc = event_dt.replace(tzinfo=KYIV_TZ).astimezone(timezone.utc).replace(tzinfo=None)

            # Check if report already exists in DB (around or after event time)
            if await check_report_exists(obj_name, event_type, event_utc):
                return

            # If we are here - report is missing!
            extra = extra_info or {}
            if event_type == 'power_change':
                p_prev = extra.get('power_prev', '')
                p_curr = extra.get('power_curr', '')
                diff_text = f" (з {p_prev} на {p_curr})" if p_prev and p_curr else ""
                msg = (
                    f"⚠️ <b>НАГАДУВАННЯ: ВІДСУТНІЙ ЗВІТ</b>\n\n"
                    f"Згідно з графіком, на ГПУ <b>{obj_name}</b> о <b>{event_time_str}</b> мала бути змінена потужність{diff_text}.\n"
                    f"Чи була змінена потужність?\n"
                    f"Минуло вже {margin} хвилин, але звіт «Статус ГПУ» ще не подано.\n\n"
                    f"☝️ Будь ласка, заповніть статус у боті!"
                )
            elif event_type == 'mode_change':
                m_prev = extra.get('mode_prev', '')
                m_curr = extra.get('mode_curr', '')
                diff_text = f" ({m_prev} ➔ {m_curr})" if m_prev and m_curr else ""
                msg = (
                    f"⚠️ <b>НАГАДУВАННЯ: ВІДСУТНІЙ ЗВІТ</b>\n\n"
                    f"Згідно з графіком, на ГПУ <b>{obj_name}</b> о <b>{event_time_str}</b> мав бути змінений режим роботи{diff_text}.\n"
                    f"Чи був змінений режим роботи?\n"
                    f"Минуло вже {margin} хвилин, але звіт «Статус ГПУ» ще не подано.\n\n"
                    f"☝️ Будь ласка, заповніть статус у боті!"
                )
            elif event_type == 'combined_change':
                p_prev = extra.get('power_prev', '')
                p_curr = extra.get('power_curr', '')
                m_prev = extra.get('mode_prev', '')
                m_curr = extra.get('mode_curr', '')
                mode_diff = f" ({m_prev} ➔ {m_curr})" if m_prev and m_curr else ""
                power_diff = f" (з {p_prev} на {p_curr})" if p_prev and p_curr else ""
                msg = (
                    f"⚠️ <b>НАГАДУВАННЯ: ВІДСУТНІЙ ЗВІТ</b>\n\n"
                    f"Згідно з графіком, на ГПУ <b>{obj_name}</b> о <b>{event_time_str}</b> мав бути змінений режим роботи{mode_diff} та потужність{power_diff}.\n"
                    f"Чи був змінений режим роботи та чи була змінена потужність?\n"
                    f"Минуло вже {margin} хвилин, але звіт «Статус ГПУ» ще не подано.\n\n"
                    f"☝️ Будь ласка, заповніть статус у боті!"
                )
            else:
                action = "ЗАПУЩЕНА" if event_type == 'start' else "ЗУПИНЕНА"
                msg = (
                    f"⚠️ <b>НАГАДУВАННЯ: ВІДСУТНІЙ ЗВІТ</b>\n\n"
                    f"Згідно з графіком, ГПУ <b>{obj_name}</b> мала бути <b>{action}</b> о <b>{event_time_str}</b>.\n"
                    f"Минуло вже {margin} хвилин, але звіт «Статус ГПУ» ще не подано.\n\n"
                    f"☝️ Будь ласка, заповніть статус у боті!"
                )
            
            # Add Interactive Buttons
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="💬 Залишити коментар", callback_data=f"remind_comment:{schedule_id}:{event_type}:{event_time_str}"),
                    InlineKeyboardButton(text="🔇 Ігнорувати", callback_data=f"remind_ignore:{schedule_id}:{event_type}:{event_time_str}")
                ]
            ])
            
            try:
                await bot.send_message(chat_id=group_id, text=msg, parse_mode="HTML", reply_markup=kb)
                await log_sent_reminder(schedule_id, event_type, event_time_str)
                logger.info(f"Sent {event_type} reminder for {obj_name} (scheduled {event_time_str})")
            except Exception as e:
                logger.error(f"Failed to send reminder to {group_id}: {e}")

            # Notify Special Group if configured (without reply_markup)
            if config.special_group_id:
                try:
                    await bot.send_message(chat_id=config.special_group_id, text=msg, parse_mode="HTML")
                    logger.info(f"Sent duplicated {event_type} reminder for {obj_name} to special group {config.special_group_id}")
                except Exception as e:
                    logger.error(f"Failed to send duplicated reminder to special group {config.special_group_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error processing {event_type} reminder for {obj_name}: {e}")
