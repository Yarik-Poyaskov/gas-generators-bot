import sqlite3

DB_PATH = "reports.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        print("🚀 Починаю міграцію: додавання колонки 'role'...")
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        conn.commit()
        print("✅ Колонка 'role' успішно додана!")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("ℹ️ Колонка 'role' вже існує.")
        else:
            print(f"❌ Помилка: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
