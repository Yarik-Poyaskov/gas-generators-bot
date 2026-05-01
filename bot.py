import asyncio
import logging
import sys
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import config
from app.db.database import init_db, get_setting
from app.handlers import (
    common, report, admin, trader, schedule_confirm, 
    groups, admin_edit, admin_settings, trader_parser, admin_broadcast,
    shifts
)
from app.middlewares.logging import ActionLoggingMiddleware
from send_summary_report import run_summary_report
from app.services.scheduler_tasks import send_admin_reminders, check_trader_confirmations
from app.services.shifts import auto_close_shifts_task, send_shift_reminders_task
from app.services.report_reminders import check_and_send_report_reminders

async def main():
    """The main function that starts the bot."""
    # Initialize the database
    await init_db()

    # Bot and Dispatcher setup
    bot = Bot(
        token=config.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Register Middlewares
    dp.update.outer_middleware(ActionLoggingMiddleware())

    # Include routers
    dp.include_router(common.cancel_router) # Highest priority: Global Cancel
    dp.include_router(trader_parser.router) # Auto-parser for group messages
    dp.include_router(groups.router)
    dp.include_router(trader.router)
    dp.include_router(schedule_confirm.router)
    dp.include_router(report.router)
    dp.include_router(admin_edit.router)
    dp.include_router(admin_settings.router)
    dp.include_router(admin_broadcast.router)
    dp.include_router(admin.router)
    dp.include_router(shifts.router)
    dp.include_router(common.router)
    
    # Setup Scheduler
    scheduler = AsyncIOScheduler(timezone="Europe/Kiev")
    
    from send_summary_report import run_summary_report
    from send_special_summary import run_special_summary_report

    # helper function to add jobs
    async def setup_jobs():
        jobs_data = [
            ("summary_report_time", run_summary_report, "job_summary", [bot]),
            ("special_summary_report_time", run_special_summary_report, "job_special_summary", [bot]),
            ("remind_schedules_time", send_admin_reminders, "job_remind", [bot]),
            ("remind_schedules_2_time", send_admin_reminders, "job_remind_2", [bot]),
            ("check_confirmations_1_time", check_trader_confirmations, "job_check_1", [bot]),
            ("check_confirmations_2_time", check_trader_confirmations, "job_check_2", [bot]),
        ]
        
        for key, func, job_id, args in jobs_data:
            time_str = await get_setting(key, "09:00")
            active_key = key.replace("_time", "_active")
            is_active = await get_setting(active_key, "1") == "1"
            
            try:
                hour, minute = map(int, time_str.split(":"))
                scheduler.add_job(
                    func, "cron", hour=hour, minute=minute, 
                    args=args, id=job_id, replace_existing=True,
                    misfire_grace_time=300
                )
                if not is_active:
                    scheduler.pause_job(job_id)
                    logging.info(f"📅 Job {job_id} ({key}) scheduled at {hour:02d}:{minute:02d} but PAUSED")
                else:
                    logging.info(f"📅 Job {job_id} ({key}) scheduled at {hour:02d}:{minute:02d} (active)")
            except Exception as e:
                logging.error(f"❌ Error scheduling {job_id}: {e}")

    await setup_jobs()
    # Add other background tasks
    reminder_interval = int(await get_setting("shift_reminder_interval", "5"))
    scheduler.add_job(auto_close_shifts_task, 'interval', minutes=15, args=[bot], id="auto_close_shifts", misfire_grace_time=300)
    scheduler.add_job(send_shift_reminders_task, 'interval', minutes=reminder_interval, args=[bot], id="send_shift_reminders", misfire_grace_time=300)
    scheduler.add_job(check_and_send_report_reminders, 'interval', minutes=5, args=[bot], id="report_event_reminders", misfire_grace_time=300)
    
    scheduler.start()

    # Start polling
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Import and setup API server
    from app.api.main import start_api_server
    
    logging.info(f"🚀 Starting Bot and API Server on port {config.api_port}...")
    
    # Run API server in the same event loop as the bot
    # This ensures smooth message sending from API via the bot
    api_task = asyncio.create_task(start_api_server(bot))
    
    # Run Bot polling in the main loop
    try:
        await dp.start_polling(bot, scheduler=scheduler)
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    except Exception as e:
        logging.error(f"❌ Error in loop: {e}")
    finally:
        # 0. Signal API server to stop first
        from app.api.main import api_server
        if api_server:
            api_server.should_exit = True
            logging.info("📡 Signaling API Server to stop...")

        # 1. Cancel API task
        api_task.cancel()
        
        # 2. Shutdown Scheduler
        if scheduler.running:
            scheduler.shutdown(wait=False)
            logging.info("📅 Scheduler stopped.")
            
        # 3. Close Bot Session
        await bot.session.close()
        logging.info("🤖 Bot session closed.")
        
        # Give a moment for final cleanup
        await asyncio.sleep(0.1)
        logging.info("🛑 Shutting down complete.")

if __name__ == "__main__":
    # Настройка лога
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler("user_actions.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    # Повышаем уровень для системных логов, чтобы не "мусорили"
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("aiogram.dispatcher").setLevel(logging.INFO)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped!")

    logging.getLogger("aiogram.dispatcher").setLevel(logging.INFO)
    
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("👋 Bot stopped by user.")
        sys.exit(0)
    except Exception as e:
        logging.error(f"❌ Fatal error: {e}")
        sys.exit(1)
