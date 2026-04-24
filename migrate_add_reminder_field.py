import asyncio
import aiosqlite

DB_PATH = "reports.db"

async def migrate_reminder_field():
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("ALTER TABLE shifts ADD COLUMN reminder_sent BOOLEAN DEFAULT 0")
            await db.commit()
            print("✅ Колонка reminder_sent успішно додана.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("ℹ️ Колонка reminder_sent вже існує.")
            else:
                print(f"❌ Помилка: {e}")

if __name__ == "__main__":
    asyncio.run(migrate_reminder_field())
