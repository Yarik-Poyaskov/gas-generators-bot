import asyncio
import aiosqlite

DB_PATH = "reports.db"

async def migrate():
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Создаем таблицу смен
        await db.execute("""
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id BIGINT NOT NULL,
                object_id INTEGER NOT NULL,
                start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                end_time DATETIME,
                planned_end_time DATETIME,
                auto_closed BOOLEAN DEFAULT 0,
                FOREIGN KEY (object_id) REFERENCES objects (id)
            )
        """)
        
        # 2. Добавляем настройку автозакрытия
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('auto_close_shifts', '0')")
        
        await db.commit()
    print("✅ Миграция shifts завершена успешно.")

if __name__ == "__main__":
    asyncio.run(migrate())
