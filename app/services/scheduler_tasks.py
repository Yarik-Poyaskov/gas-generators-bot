import re
import logging
from aiogram import Bot
from datetime import datetime, timedelta

from app.config import config
from app.db.database import get_schedules_for_report, add_schedule_reminder, has_any_schedule

logger = logging.getLogger(__name__)

async def send_admin_reminders(bot: Bot):
    """Sends a reminder to all admins to send schedules if none were submitted yet."""
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_db_str = tomorrow.strftime("%Y-%m-%d")

    # Check if any schedule for tomorrow already exists
    already_submitted = await has_any_schedule(tomorrow_db_str)
    if already_submitted:
        logger.info(f"Skipping admin reminder: some schedules for {tomorrow_db_str} already submitted.")
        return

    text = "🔔 <b>Нагадування:</b> Пора відправити графіки по об'єктах!"
    for admin_id in config.admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to send reminder to {admin_id}: {e}")

    # Also send to special group if configured
    if config.special_group_id:
        try:
            await bot.send_message(chat_id=config.special_group_id, text=text, parse_mode="HTML")
            logger.info(f"Sent admin reminder to special group {config.special_group_id}")
        except Exception as e:
            logger.error(f"Failed to send reminder to special group {config.special_group_id}: {e}")

async def check_trader_confirmations(bot: Bot):
    """
    Generates report for tomorrow, sends it to admins, 
    and notifies groups of unconfirmed objects ONLY if the schedule was submitted by trader.
    """
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_db_str = tomorrow.strftime("%Y-%m-%d") # Format for DB query
    tomorrow_display_str = tomorrow.strftime("%d.%m.%Y") # Format for display
    
    # Get all schedules (including those NOT submitted yet)
    schedules = await get_schedules_for_report(tomorrow_db_str)
    
    if not schedules:
        logger.info(f"No objects/schedules found for {tomorrow_db_str}")
        return

    # 1. Build Report for Admins (Full report)
    report_text = f"📊 <b>СТАТУС ПОДАНИХ ГРАФІКІВ (НА ЗАВТРА)</b>\n"
    report_text += f"📅 Дата графіка: {tomorrow_display_str}\n"
    report_text += f"⏰ Час звіту: {datetime.now().strftime('%H:%M')}\n\n"

    to_notify_groups = []

    for s in schedules:
        full_tc_name = s.get('tc_name', 'Unknown')
        match_name = re.search(r'\((.*?)\)', full_tc_name)
        display_tc_name = match_name.group(1) if match_name else full_tc_name

        if not s['schedule_id']:
            # Not submitted by trader
            status_icon = "❌"
            work_status = "ГРАФІК НЕ ПОДАНО"
            confirmed_info = "\n   └ <b>ТРЕЙДЕР НЕ ПОДАВ ДАНІ</b>"
        else:
            status_icon = "✅" if s['confirmed_by'] else "⏳"
            work_status = "НЕ ПРАЦЮЄ" if s['is_not_working'] else "Є ГРАФІК"
            if s['confirmed_by']:
                confirmed_info = f"\n   └ Підтвердив: {s['confirmed_user_name']}"
            else:
                confirmed_info = "\n   └ <b>ОЧІКУЄ ПІДТВЕРДЖЕННЯ</b>"
                # ONLY notify group if schedule was submitted but not confirmed
                if s.get('telegram_group_id'):
                    to_notify_groups.append(s)
        
        report_text += f"{status_icon} <b>{display_tc_name}</b>: {work_status}{confirmed_info}\n\n"

    # Send report to all admins
    for admin_id in config.admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=report_text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to send confirmation report to admin {admin_id}: {e}")

    # 2. Notify Groups of Unconfirmed Objects (ONLY if trader submitted data)
    for s in to_notify_groups:
        group_id = s['telegram_group_id']
        try:
            msg = "⚠️ <b>Увага!</b> Графік на завтра ще не підтверджено. Будь ласка, перевірте."
            sent_msg = await bot.send_message(chat_id=group_id, text=msg, parse_mode="HTML")
            
            # Save reminder message ID to DB for future deletion
            if s.get('schedule_id'):
                await add_schedule_reminder(s['schedule_id'], group_id, sent_msg.message_id)
                
        except Exception as e:
            logger.error(f"Failed to notify group {group_id} for object {s['tc_name']}: {e}")
