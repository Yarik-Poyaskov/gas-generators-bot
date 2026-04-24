from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.filters.is_admin import IsAdmin
from app.db.database import get_setting, update_setting
from app.keyboards.inline import (
    get_settings_keyboard, get_scheduler_mgmt_kb, 
    get_scheduler_hour_kb, get_scheduler_minute_kb
)
from send_summary_report import run_summary_report
from app.services.scheduler_tasks import send_admin_reminders, check_trader_confirmations

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

@router.message(F.text == "Налаштування")
async def cmd_admin_settings(message: Message):
    pm = await get_setting("notify_trader_pm", "1") == "1"
    groups = await get_setting("notify_trader_groups", "1") == "1"
    hide_not_working = await get_setting("hide_not_working_in_short", "0") == "1"
    auto_close = await get_setting("auto_close_shifts", "0") == "1"
    reminder_interval = int(await get_setting("shift_reminder_interval", "5"))
    
    await message.answer(
        "⚙️ **Налаштування бота**\n\nТут ви можете керувати сповіщеннями та розкладом автоматичних завдань:",
        reply_markup=get_settings_keyboard(pm, groups, hide_not_working, auto_close, reminder_interval)
    )

@router.callback_query(F.data == "back_to_settings")
@router.callback_query(F.data == "open_settings")
async def back_to_settings(callback: CallbackQuery):
    pm = await get_setting("notify_trader_pm", "1") == "1"
    groups = await get_setting("notify_trader_groups", "1") == "1"
    hide_not_working = await get_setting("hide_not_working_in_short", "0") == "1"
    auto_close = await get_setting("auto_close_shifts", "0") == "1"
    reminder_interval = int(await get_setting("shift_reminder_interval", "5"))
    
    await callback.message.edit_text(
        "⚙️ **Налаштування бота**\n\nТут ви можете керувати сповіщеннями та розкладом автоматичних завдань:",
        reply_markup=get_settings_keyboard(pm, groups, hide_not_working, auto_close, reminder_interval)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("toggle_setting:"))
async def process_toggle_setting(callback: CallbackQuery):
    parts = callback.data.split(":")
    key = parts[1]
    new_val = parts[2]
    
    await update_setting(key, new_val)
    pm = await get_setting("notify_trader_pm", "1") == "1"
    groups = await get_setting("notify_trader_groups", "1") == "1"
    hide_not_working = await get_setting("hide_not_working_in_short", "0") == "1"
    auto_close = await get_setting("auto_close_shifts", "0") == "1"
    reminder_interval = int(await get_setting("shift_reminder_interval", "5"))
    
    await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard(pm, groups, hide_not_working, auto_close, reminder_interval))
    await callback.answer("Налаштування оновлено")

@router.callback_query(F.data == "set_reminder_interval_list")
async def set_reminder_interval_list(callback: CallbackQuery):
    from app.keyboards.inline import get_reminder_interval_keyboard
    await callback.message.edit_text(
        "⏱ **Виберіть інтервал перевірки нагадувань**\n\nЯк часто бот буде перевіряти смену для відправки нагадувань:",
        reply_markup=get_reminder_interval_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("set_rem_int:"))
async def set_reminder_interval(callback: CallbackQuery, scheduler: AsyncIOScheduler):
    interval = int(callback.data.split(":")[1])
    await update_setting("shift_reminder_interval", str(interval))
    
    # Update scheduler job
    try:
        scheduler.reschedule_job("send_shift_reminders", trigger='interval', minutes=interval)
        await callback.answer(f"✅ Інтервал змінено на {interval} хв", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Помилка планувальника: {e}", show_alert=True)
    
    await back_to_settings(callback)

# --- Scheduler Management ---

@router.callback_query(F.data == "open_scheduler_mgmt")
async def open_scheduler_mgmt(callback: CallbackQuery):
    jobs_info = [
        ("📊 Підсумковий звіт", await get_setting("summary_report_time", "09:40"), "summary_report_time", await get_setting("summary_report_active", "1") == "1"),
        ("🔔 Нагадування 1", await get_setting("remind_schedules_time", "13:00"), "remind_schedules_time", await get_setting("remind_schedules_active", "1") == "1"),
        ("🔔 Нагадування 2", await get_setting("remind_schedules_2_time", "15:00"), "remind_schedules_2_time", await get_setting("remind_schedules_2_active", "1") == "1"),
        ("🔍 Перевірка 1", await get_setting("check_confirmations_1_time", "14:00"), "check_confirmations_1_time", await get_setting("check_confirmations_1_active", "1") == "1"),
        ("🔍 Перевірка 2", await get_setting("check_confirmations_2_time", "15:00"), "check_confirmations_2_time", await get_setting("check_confirmations_2_active", "1") == "1"),
    ]
    await callback.message.edit_text(
        "📅 **Планувальник завдань**\n\nОберіть завдання для зміни часу виконання або увімкніть/вимкніть його:",
        reply_markup=get_scheduler_mgmt_kb(jobs_info)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("toggle_job:"))
async def process_toggle_job(callback: CallbackQuery, scheduler: AsyncIOScheduler):
    parts = callback.data.split(":")
    key = parts[1]
    new_active_val = parts[2] # "1" or "0"
    
    active_key = key.replace("_time", "_active")
    await update_setting(active_key, new_active_val)
    
    job_map = {
        "summary_report_time": "job_summary",
        "remind_schedules_time": "job_remind",
        "remind_schedules_2_time": "job_remind_2",
        "check_confirmations_1_time": "job_check_1",
        "check_confirmations_2_time": "job_check_2",
    }
    job_id = job_map.get(key)
    
    if job_id:
        try:
            if new_active_val == "1":
                scheduler.resume_job(job_id)
                msg = "✅ Завдання активовано"
            else:
                scheduler.pause_job(job_id)
                msg = "⏸ Завдання призупинено"
            await callback.answer(msg)
        except Exception as e:
            await callback.answer(f"❌ Помилка планувальника: {e}", show_alert=True)
    
    await open_scheduler_mgmt(callback)

@router.callback_query(F.data.startswith("edit_job:"))
async def edit_job_time(callback: CallbackQuery, state: FSMContext):
    setting_key = callback.data.split(":")[1]
    await state.update_data(edit_sched_key=setting_key)
    await callback.message.edit_text("Оберіть годину:", reply_markup=get_scheduler_hour_kb())
    await callback.answer()

@router.callback_query(F.data == "back_to_sched_hours")
async def back_to_sched_hours(callback: CallbackQuery):
    await callback.message.edit_text("Оберіть годину:", reply_markup=get_scheduler_hour_kb())
    await callback.answer()

@router.callback_query(F.data.startswith("sched_h:"))
async def select_sched_minute(callback: CallbackQuery):
    hour = callback.data.split(":")[1]
    await callback.message.edit_text(f"Година: {hour}. Оберіть хвилини:", reply_markup=get_scheduler_minute_kb(hour))
    await callback.answer()

@router.callback_query(F.data.startswith("sched_m:"))
async def save_sched_time(callback: CallbackQuery, state: FSMContext, scheduler: AsyncIOScheduler, bot: Bot):
    parts = callback.data.split(":")
    hour, minute = parts[1], parts[2]
    new_time = f"{hour}:{minute}"
    
    data = await state.get_data()
    setting_key = data.get("edit_sched_key")
    if not setting_key:
        await callback.answer("Помилка: ключ не знайдено.")
        return

    # 1. Update DB
    await update_setting(setting_key, new_time)
    
    # 2. Reschedule Job
    job_map = {
        "summary_report_time": ("job_summary", run_summary_report),
        "remind_schedules_time": ("job_remind", send_admin_reminders),
        "remind_schedules_2_time": ("job_remind_2", send_admin_reminders),
        "check_confirmations_1_time": ("job_check_1", check_trader_confirmations),
        "check_confirmations_2_time": ("job_check_2", check_trader_confirmations),
    }
    
    job_id, func = job_map[setting_key]
    try:
        scheduler.reschedule_job(
            job_id, 
            trigger='cron', 
            hour=int(hour), 
            minute=int(minute)
        )
        
        # Check if it should be paused
        active_key = setting_key.replace("_time", "_active")
        is_active = await get_setting(active_key, "1") == "1"
        if not is_active:
            scheduler.pause_job(job_id)
            
        await callback.answer(f"✅ Час змінено на {new_time}", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Помилка планувальника: {e}", show_alert=True)

    # Return to mgmt list
    await open_scheduler_mgmt(callback)
