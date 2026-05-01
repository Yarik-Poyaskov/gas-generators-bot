import asyncio
import aiosqlite
import os

DB_PATH = "reports.db"

async def migrate():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database {DB_PATH} not found.")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        print("🚀 Starting migration: monthly_reports table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS monthly_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                object_id INTEGER,
                user_id INTEGER,
                report_month INTEGER,
                report_year INTEGER,
                energy_mwh REAL,
                gas_start REAL,
                gas_end REAL,
                gas_coef REAL,
                gas_total REAL,
                oil_start REAL,
                oil_end REAL,
                oil_added REAL,
                oil_total REAL,
                spec_gas REAL,
                spec_oil REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (object_id) REFERENCES objects (id)
            )
        """)
        await db.commit()
        print("✅ Migration successful: monthly_reports table created.")

if __name__ == "__main__":
    asyncio.run(migrate())
