import sqlite3
import os

def migrate():
    db_path = "reports.db"
    if not os.path.exists(db_path):
        print(f"База данных {db_path} не найдена. Нечего мигрировать.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Проверяем, была ли уже проведена миграция (проверяем наличие колонки phone_number)
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if "phone_number" in columns:
        print("Миграция уже была применена ранее.")
        conn.close()
        return

    print("Начинаю миграцию таблицы 'users'...")
    try:
        # 1. Создаем временную таблицу с новой структурой
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id BIGINT UNIQUE,
                phone_number TEXT UNIQUE,
                full_name TEXT,
                username TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Копируем существующие данные из старой таблицы
        cursor.execute("""
            INSERT INTO users_new (user_id, full_name, username, created_at, updated_at)
            SELECT user_id, full_name, username, created_at, updated_at FROM users
        """)

        # 3. Удаляем старую таблицу
        cursor.execute("DROP TABLE users")

        # 4. Переименовываем новую таблицу в 'users'
        cursor.execute("ALTER TABLE users_new RENAME TO users")

        conn.commit()
        print("Миграция успешно завершена!")
        
        # Проверка структуры после миграции
        cursor.execute("PRAGMA table_info(users)")
        new_columns = cursor.fetchall()
        print("\nНовая структура таблицы 'users':")
        for col in new_columns:
            print(f"- {col[1]} ({col[2]})")

    except Exception as e:
        conn.rollback()
        print(f"Ошибка во время миграции: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
