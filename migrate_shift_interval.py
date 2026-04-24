import asyncio
import aiosqlite

DB_PATH = "reports.db"

async def migrate_settings():
    async with aiosqlite.connect(DB_PATH) as db:
        # Добавляем настройку интервала (по умолчанию 5 минут)
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('shift_reminder_interval', '5')")
        await db.commit()
        print("✅ Налаштування shift_reminder_interval додано до бази даних.")

if __name__ == "__main__":
    asyncio.run(migrate_settings())
