import asyncio
import aiosqlite
import os

DB_PATH = 'reports.db'

async def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        # Add is_required to objects table
        try:
            await db.execute("ALTER TABLE objects ADD COLUMN is_required INTEGER DEFAULT 1")
            print("Added 'is_required' column to 'objects' table.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("Column 'is_required' already exists.")
            else:
                print(f"Error adding column: {e}")

        # Add alert_checklist_time to settings table if not exists
        try:
            # We don't need to alter settings table, just insert a default if it's missing
            cursor = await db.execute("SELECT key FROM settings WHERE key = 'alert_checklist_time'")
            row = await cursor.fetchone()
            if not row:
                await db.execute("INSERT INTO settings (key, value) VALUES ('alert_checklist_time', '09:20')")
                print("Added default 'alert_checklist_time' to 'settings' table.")
            else:
                print("'alert_checklist_time' already exists in 'settings'.")
        except Exception as e:
            print(f"Error updating settings: {e}")

        await db.commit()
    print("Migration finished.")

if __name__ == '__main__':
    asyncio.run(migrate())
