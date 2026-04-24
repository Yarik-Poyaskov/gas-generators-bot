import asyncio
import aiosqlite
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from app.config import config
from datetime import datetime

DB_PATH = "reports.db"

async def test_send_last_report():
    """
    Fetches the latest report from the database and sends it as a simplified 
    text report to the SPECIAL_GROUP_ID.
    """
    print("--- ТЕСТ ВІДПРАВКИ У СПЕЦ-ГРУПУ ---")
    
    if not config.special_group_id:
        print("❌ Помилка: SPECIAL_GROUP_ID не налаштований у .env")
        return

    # 1. Получаем последний отчет из базы
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM reports ORDER BY id DESC LIMIT 1")
            report = await cursor.fetchone()
    except Exception as e:
        print(f"❌ Помилка підключення до БД: {e}")
        return

    if not report:
        print("❌ Помилка: У базі немає жодного звіту для тесту.")
        return

    print(f"✅ Знайдено звіт ID:{report['id']} (Об'єкт: {report['tc_name']})")

    # 2. Формируем краткий текст (в точности как в боте)
    # Если дата в базе в формате YYYY-MM-DD HH:MM:SS, переделаем в DD.MM.YYYY
    try:
        dt = datetime.strptime(report['created_at'], "%Y-%m-%d %H:%M:%S")
        display_date = dt.strftime("%d.%m.%Y")
    except Exception:
        display_date = report['created_at']

    special_summary = f"""
<b>Об'єкт:</b> {report['tc_name']}
<b>Дата:</b> {display_date}

<b>1. Режим роботи:</b> {report['work_mode']}
<b>2. Час запуску:</b> {report['start_time']}
<b>3. Навантаження:</b> {report['load_power_percent']} % / {report['load_power_kw']} кВт
<b>4. Статус роботи:</b> {report['gpu_status']}
    """

    # 3. Отправляем в Telegram
    bot = Bot(
        token=config.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    try:
        await bot.send_message(
            chat_id=config.special_group_id, 
            text=special_summary
        )
        print(f"🚀 Звіт успішно відправлено у групу {config.special_group_id}")
    except Exception as e:
        print(f"❌ Помилка відправки в Telegram: {e}")
        print("Порада: переконайтеся, що бот доданий у групу і має права на відправку повідомлень.")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    if asyncio.get_event_loop_policy().__class__.__name__ == 'WindowsProactorEventLoopPolicy':
        # Avoid 'Event loop is closed' errors on Windows at exit
        pass
    asyncio.run(test_send_last_report())
