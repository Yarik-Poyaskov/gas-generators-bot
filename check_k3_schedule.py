import asyncio
import aiosqlite
import json
from datetime import date

async def check():
    async with aiosqlite.connect('reports.db') as db:
        db.row_factory = aiosqlite.Row
        today = "2026-04-27"
        c = await db.execute("SELECT s.id, s.schedule_json, o.name FROM trader_schedules s JOIN objects o ON s.object_id = o.id WHERE o.name LIKE '%K3%' AND s.target_date = ?", (today,))
        r = await c.fetchone()
        if r:
            print(f"Object: {r['name']}")
            print(f"Schedule ID: {r['id']}")
            print(f"Schedule JSON: {r['schedule_json']}")
            
            # Check if reminder was already sent
            c = await db.execute("SELECT * FROM schedule_event_reminders WHERE schedule_id = ?", (r['id'],))
            reminders = await c.fetchall()
            print(f"Reminders sent for this schedule: {[dict(rem) for rem in reminders]}")
            
            # Check if STOP report exists
            c = await db.execute("SELECT created_at, time_type FROM reports WHERE tc_name LIKE '%K3%' AND date(created_at) >= date('now', '-1 day') ORDER BY created_at DESC")
            reports = await c.fetchall()
            print(f"Latest reports for K3: {[dict(rep) for rep in reports[:3]]}")
        else:
            print("No schedule found for K3 today")

if __name__ == "__main__":
    asyncio.run(check())
