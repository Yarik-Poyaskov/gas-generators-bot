import sqlite3

def migrate():
    conn = sqlite3.connect('reports.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(reports)")
        columns = [column[1] for column in cursor.fetchall()]
        
        new_columns = [
            ('pressure_intercooler_before', 'REAL'),
            ('pressure_intercooler_after', 'TEXT'),
            ('pressure_engine_before', 'REAL'),
            ('pressure_engine_after', 'TEXT'),
            ('battery_voltage_haas', 'TEXT'),
            ('bearing_lubrication_limit', 'REAL')
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in columns:
                print(f"Adding '{col_name}' ({col_type}) column to 'reports' table...")
                cursor.execute(f"ALTER TABLE reports ADD COLUMN {col_name} {col_type}")
                print(f"Column '{col_name}' added.")
            else:
                print(f"Column '{col_name}' already exists.")
        
        conn.commit()
        print("Migration successful!")
            
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
