import asyncio
import aiosqlite
import os

DB_PATH = "reports.db"

async def prepare_for_production():
    """
    Deletes all records from the 'reports' table and resets its auto-increment ID.
    Keeps users, objects, and their links intact.
    """
    if not os.path.exists(DB_PATH):
        print(f"Файл бази даних {DB_PATH} не знайдено.")
        return

    print("--- ПІДГОТОВКА ДО ПРОДАКШНУ ---")
    print("Увага! Цей скрипт видалить ВСІ звіти з бази даних.")
    print("Користувачі, об'єкти та їх зв'язки залишаться недоторканими.")
    
    confirm = input("\nВи впевнені, що хочете ВИДАЛИТИ ВСІ ЗВІТИ? (y/n): ")
    if confirm.lower() != 'y':
        print("Дію скасовано.")
        return

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # 1. Удаляем все записи из таблицы отчетов
            await db.execute("DELETE FROM reports")
            
            # 2. Сбрасываем счетчик AUTOINCREMENT для таблицы reports
            # Это заставит новые отчеты снова начинаться с ID: 1
            try:
                await db.execute("DELETE FROM sqlite_sequence WHERE name='reports'")
            except Exception:
                # Таблица sqlite_sequence может не существовать, если еще не было записей
                pass
            
            await db.commit()
            print("\n✅ Всі звіти успішно видалені.")
            print("ℹ️ Таблиці 'users', 'objects' та 'user_objects' збережені.")

    except Exception as e:
        print(f"❌ Помилка при роботі з БД: {e}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(prepare_for_production())
