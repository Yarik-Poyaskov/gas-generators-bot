import asyncio
import aiosqlite
import os
import sys # Added sys import for Python version check if needed

# Ensure DB_PATH is correctly pointing to your database
# This assumes reports.db is in the same directory as the script, or in the project root if script is also in root
# Corrected DB_PATH to point to the reports.db in the project root,
# assuming bot.py creates it there.
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports.db")

async def export_reports_to_console():
    """
    Exports all reports from the database and prints them to the console.
    """
    print(f"DEBUG: Попытка подключения к базе данных: {DB_PATH}")
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row # To get dictionary-like rows with column names
            cursor = await db.execute("SELECT * FROM reports ORDER BY created_at DESC")
            rows = await cursor.fetchall()

            if not rows:
                print("В базе данных нет отчетов для вывода.")
                return

            print("\n--- Отчеты из базы данных ---")
            for i, row in enumerate(rows):
                print(f"\n--- Отчет #{i+1} ---")
                row_dict = dict(row) # Преобразуем sqlite3.Row в обычный словарь
                for key, value in row_dict.items():
                    print(f"{key}: {value}")
            print("\n--- Конец отчетов ---")

    except Exception as e:
        print(f"Произошла ошибка при подключении/запросе к БД: {e}")

if __name__ == "__main__":
    if os.name == 'nt': # Проверка на Windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(export_reports_to_console())
