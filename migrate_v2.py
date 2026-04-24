import sqlite3

def migrate():
    conn = sqlite3.connect('reports.db')
    cursor = conn.cursor()
    
    try:
        # 1. Добавляем колонку time_type в reports
        cursor.execute("PRAGMA table_info(reports)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'time_type' not in columns:
            print("Adding 'time_type' column to 'reports' table...")
            cursor.execute("ALTER TABLE reports ADD COLUMN time_type TEXT")
            print("Column 'time_type' added.")
        
        # 2. Пытаемся заполнить time_type для старых записей на основе статуса
        # Это только для того, чтобы на сайте сразу всё стало красиво
        print("Updating old records context...")
        cursor.execute("UPDATE reports SET time_type = 'start' WHERE gpu_status LIKE '%стабільна%' OR gpu_status LIKE '%запуск%'")
        cursor.execute("UPDATE reports SET time_type = 'stop' WHERE gpu_status LIKE '%не працює%' OR gpu_status LIKE '%аварії%' OR gpu_status LIKE '%зупинка%'")
        
        conn.commit()
        print("Migration successful!")
            
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
