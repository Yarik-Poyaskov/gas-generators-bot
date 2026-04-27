import asyncio
import aiosqlite
import json
from datetime import date

async def check():
    async with aiosqlite.connect('reports.db') as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM objects WHERE name LIKE '%K8%'")
        obj = await c.fetchone()
        if not obj:
            print("K8 not found")
            return
        
        print(f"Object: {obj['name']} (ID: {obj['id']})")
        
        today = date.today().isoformat()
        c = await db.execute("SELECT * FROM reports WHERE tc_name LIKE ? AND date(created_at) = ? ORDER BY created_at DESC LIMIT 1", (f"%{obj['name']}%", today))
        r = await c.fetchone()
        if r:
            print(f"Latest Report today: Status={r['gpu_status']}, TimeType={r['time_type']}, CreatedAt={r['created_at']}, StartTime={r['start_time']}")
        else:
            print("No report today")

        c = await db.execute("SELECT * FROM trader_schedules WHERE object_id = ? AND target_date = ?", (obj['id'], today))
        s = await c.fetchone()
        if s:
            print(f"Schedule: {s['schedule_json']}")
        else:
            print("No schedule today")

if __name__ == "__main__":
    asyncio.run(check())
