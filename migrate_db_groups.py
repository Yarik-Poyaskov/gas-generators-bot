import asyncio
import aiosqlite

DB_PATH = "reports.db"

async def migrate():
    async with aiosqlite.connect(DB_PATH) as db:
        print("Migrating database...")
        
        # 1. Create telegram_groups table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS telegram_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id BIGINT UNIQUE NOT NULL,
                title TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Table 'telegram_groups' created/verified.")

        # 2. Add telegram_group_id to objects table
        try:
            await db.execute("ALTER TABLE objects ADD COLUMN telegram_group_id BIGINT")
            print("Column 'telegram_group_id' added to 'objects' table.")
        except aiosqlite.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("Column 'telegram_group_id' already exists in 'objects' table.")
            else:
                print(f"Error adding column: {e}")

        await db.commit()
        print("Migration completed successfully.")

if __name__ == "__main__":
    asyncio.run(migrate())
