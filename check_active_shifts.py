import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = "reports.db"

def check_active_shifts():
    if not os.path.exists(DB_PATH):
        print(f"❌ База даних {DB_PATH} не знайдена.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = """
        SELECT 
            o.name as object_name, 
            u.full_name as user_name, 
            s.start_time
        FROM shifts s
        JOIN objects o ON s.object_id = o.id
        JOIN users u ON s.user_id = u.user_id
        WHERE s.end_time IS NULL
        ORDER BY o.name
    """
    
    try:
        cursor.execute(query)
        rows = cursor.fetchall()

        print("\n" + "="*85)
        print(f"{'ОБ`ЄКТ':<35} | {'СПІВРОБІТНИК':<25} | {'ПОЧАТОК (МІСЦЕВИЙ)':<20}")
        print("-" * 85)

        if not rows:
            print(f"{'НЕМАЄ АКТИВНИХ ЗМІН':^85}")
        else:
            for row in rows:
                # Конвертація з UTC у Місцевий (+3 години)
                try:
                    utc_time = datetime.strptime(row['start_time'], "%Y-%m-%d %H:%M:%S")
                    local_time = utc_time + timedelta(hours=3)
                    local_time_str = local_time.strftime("%d.%m %H:%M")
                except:
                    local_time_str = row['start_time'] # На випадок помилки парсингу

                print(f"{row['object_name']:<35} | {row['user_name']:<25} | {local_time_str:<20}")
        
        print("="*85 + "\n")

    except sqlite3.Error as e:
        print(f"❌ Помилка бази даних: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_active_shifts()
