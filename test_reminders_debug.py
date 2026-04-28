import asyncio
import json
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo
import aiosqlite

DB_PATH = "reports.db"
KYIV_TZ = ZoneInfo("Europe/Kiev")

async def get_setting(key, default="20"):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row[0] if row else default

async def check_debug():
    print(f"--- DEBUG REMINDERS ---")
    now_kyiv = datetime.now(KYIV_TZ)
    today_db = now_kyiv.strftime("%Y-%m-%d")
    margin = int(await get_setting('report_reminder_margin', '20'))
    
    print(f"Now (Kyiv): {now_kyiv.strftime('%H:%M:%S')}")
    print(f"Today: {today_db}")
    print(f"Margin: {margin} min")
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Get all schedules for today
        query = """
            SELECT o.name as tc_name, o.telegram_group_id, s.id as schedule_id, s.schedule_json, s.is_not_working
            FROM objects o 
            JOIN trader_schedules s ON o.id = s.object_id 
            WHERE s.target_date = ?
        """
        cursor = await db.execute(query, (today_db,))
        schedules = await cursor.fetchall()
        
        if not schedules:
            print("No schedules found for today.")
            return

        for s in schedules:
            if s['is_not_working']:
                print(f"Object {s['tc_name']}: marked as NOT WORKING.")
                continue
                
            intervals = json.loads(s['schedule_json'])
            print(f"\nObject: {s['tc_name']} (Group: {s['telegram_group_id']})")
            
            for interval in intervals:
                for event_type in ['start', 'stop']:
                    time_str = interval.get(event_type)
                    if not time_str: continue
                    
                    event_h, event_m = map(int, time_str.split(':'))
                    event_dt = now_kyiv.replace(hour=event_h, minute=event_m, second=0, microsecond=0)
                    
                    threshold = event_dt + timedelta(minutes=margin)
                    expired = event_dt + timedelta(hours=2)
                    
                    status = "WAITING"
                    if now_kyiv > threshold:
                        status = "MISSING?"
                    if now_kyiv > expired:
                        status = "EXPIRED (Too old)"
                    
                    print(f"  - {event_type.upper()} at {time_str}: Status={status} (Threshold: {threshold.strftime('%H:%M')})")
                    
                    if status == "MISSING?":
                        # Check report
                        c = await db.execute("SELECT 1 FROM reports WHERE tc_name LIKE ? AND time_type = ? AND date(created_at) = ?", 
                                           (f"%{s['tc_name']}%", event_type, today_db))
                        has_report = await c.fetchone() is not None
                        
                        # Check if reminder sent
                        c = await db.execute("SELECT 1 FROM schedule_event_reminders WHERE schedule_id = ? AND event_type = ? AND event_time = ?",
                                           (s['schedule_id'], event_type, time_str))
                        sent = await c.fetchone() is not None
                        
                        print(f"    Report exists: {has_report}")
                        print(f"    Reminder already sent: {sent}")
                        
                        if not has_report and not sent:
                            print(f"    >>> SHOULD SEND REMINDER NOW <<<")

if __name__ == "__main__":
    asyncio.run(check_debug())
