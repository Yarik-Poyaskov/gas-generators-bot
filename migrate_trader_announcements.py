import sqlite3
import os

db_path = "reports.db"

def migrate():
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check current columns
    cursor.execute("PRAGMA table_info(trader_announcements);")
    columns = [col[1] for col in cursor.fetchall()]

    added = []
    
    if "object_id" not in columns:
        print("Adding 'object_id' column to trader_announcements...")
        cursor.execute("ALTER TABLE trader_announcements ADD COLUMN object_id INTEGER;")
        added.append("object_id")

    if "message_type" not in columns:
        print("Adding 'message_type' column to trader_announcements...")
        cursor.execute("ALTER TABLE trader_announcements ADD COLUMN message_type TEXT;")
        added.append("message_type")

    if added:
        conn.commit()
        print(f"Successfully added columns: {', '.join(added)}")
    else:
        print("No migration needed. All columns exist.")

    conn.close()

if __name__ == "__main__":
    migrate()
