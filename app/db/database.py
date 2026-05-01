import aiosqlite
import json
import logging
from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, Optional, List

DB_PATH = "reports.db"

async def init_db():
    """Initializes the database and creates tables if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id BIGINT NOT NULL,
                username TEXT,
                full_name TEXT,
                tc_name TEXT,
                work_mode TEXT,
                start_time TEXT,
                load_power_percent TEXT,
                load_power_kw TEXT,
                gpu_status TEXT,
                battery_voltage TEXT,
                pressure_before REAL,
                pressure_after REAL,
                total_mwh REAL,
                total_hours REAL,
                oil_sampling_limit REAL,
                photo_multimeter_id TEXT,
                photo_shos_id TEXT,
                time_type TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id BIGINT UNIQUE,
                phone_number TEXT UNIQUE,
                full_name TEXT,
                username TEXT,
                role TEXT DEFAULT 'user',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("CREATE TABLE IF NOT EXISTS objects (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, telegram_group_id BIGINT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
        await db.execute("CREATE TABLE IF NOT EXISTS telegram_groups (id INTEGER PRIMARY KEY AUTOINCREMENT, tg_id BIGINT UNIQUE NOT NULL, title TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
        await db.execute("CREATE TABLE IF NOT EXISTS user_objects (user_db_id INTEGER, object_id INTEGER, PRIMARY KEY (user_db_id, object_id), FOREIGN KEY (user_db_id) REFERENCES users (id) ON DELETE CASCADE, FOREIGN KEY (object_id) REFERENCES objects (id) ON DELETE CASCADE)")
        await db.execute("CREATE TABLE IF NOT EXISTS trader_schedules (id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER NOT NULL, trader_id BIGINT NOT NULL, target_date TEXT NOT NULL, schedule_json TEXT, is_not_working BOOLEAN DEFAULT 0, confirmed_by INTEGER, confirmed_at DATETIME, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (object_id) REFERENCES objects (id), FOREIGN KEY (confirmed_by) REFERENCES users (id))")
        await db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS web_auth_codes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id BIGINT NOT NULL, code TEXT NOT NULL, expires_at DATETIME NOT NULL)")
        await db.execute("CREATE TABLE IF NOT EXISTS trader_announcements (id INTEGER PRIMARY KEY AUTOINCREMENT, trader_id BIGINT NOT NULL, target_date TEXT NOT NULL, chat_id BIGINT NOT NULL, message_id BIGINT NOT NULL, object_id INTEGER, message_type TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
        await db.execute("CREATE TABLE IF NOT EXISTS schedule_reminders (id INTEGER PRIMARY KEY AUTOINCREMENT, schedule_id INTEGER NOT NULL, chat_id BIGINT NOT NULL, message_id BIGINT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (schedule_id) REFERENCES trader_schedules (id) ON DELETE CASCADE)")
        await db.execute("CREATE TABLE IF NOT EXISTS broadcasts (id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id BIGINT NOT NULL, text TEXT, photo_id TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
        await db.execute("CREATE TABLE IF NOT EXISTS broadcast_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, broadcast_id INTEGER NOT NULL, chat_id BIGINT NOT NULL, message_id BIGINT NOT NULL, is_pinned BOOLEAN DEFAULT 0, FOREIGN KEY (broadcast_id) REFERENCES broadcasts (id) ON DELETE CASCADE)")
        
        await db.commit()

        # Default settings
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('summary_report_time', '09:40')")
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('remind_schedules_time', '13:00')")
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('remind_schedules_2_time', '15:00')")
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('check_confirmations_1_time', '14:00')")
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('check_confirmations_2_time', '15:00')")
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('summary_report_active', '1')")
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('special_summary_report_time', '10:00')")
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('special_summary_report_active', '1')")
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('remind_schedules_active', '1')")
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('remind_schedules_2_active', '1')")
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('check_confirmations_1_active', '1')")
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('check_confirmations_2_active', '1')")
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('hide_not_working_in_short', '0')")
        await db.commit()

# --- Report Functions ---

async def add_report(data: Dict[str, Any]):
    """Adds a new report to the database."""
    time_label = data.get("time_label", "")
    time_type = None
    if "запуск" in time_label.lower():
        time_type = "start"
    elif "зупин" in time_label.lower():
        time_type = "stop"
    
    if not time_type:
        status = (data.get("gpu_status") or "").lower()
        if "стабільна" in status or "запуск" in status:
            time_type = "start"
        else:
            time_type = "stop"

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO reports (
                user_id, username, full_name, tc_name, work_mode, start_time,
                load_power_percent, load_power_kw,
                gpu_status, battery_voltage, pressure_before, pressure_after,
                total_mwh, total_hours, oil_sampling_limit,
                photo_multimeter_id, photo_shos_id, time_type, is_short
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("user_id"), data.get("username"), data.get("full_name"),
                data.get("tc_name"), data.get("work_mode"), data.get("start_time"),
                data.get("load_power_percent"), data.get("load_power_kw"),
                data.get("gpu_status"), data.get("battery_voltage"),
                data.get("pressure_before"), data.get("pressure_after"),
                data.get("total_mwh"), data.get("total_hours"),
                data.get("oil_sampling_limit"), data.get("photo_multimeter_id"),
                data.get("photo_shos_id"), time_type, 1 if data.get("is_short") else 0
            ),
        )
        await db.commit()

async def get_objects_with_latest_status():
    """Returns all objects with their latest report data and current schedule for Web API.
    All data (status, power, mode) is taken ONLY from reports created TODAY.
    Power values are taken specifically from 'Short Reports' (is_short=1).
    """
    today_str = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Main query for overall status (ONLY TODAY)
        query = """
            SELECT o.id, o.name, o.telegram_group_id,
                   r.work_mode, r.gpu_status, 
                   r.start_time, r.time_type, r.created_at as last_report_at, r.full_name as reported_by,
                   (SELECT load_power_percent FROM reports 
                    WHERE tc_name LIKE '%' || o.name || '%' AND is_short = 1 AND date(created_at) = ?
                    ORDER BY created_at DESC LIMIT 1) as load_power_percent,
                   (SELECT load_power_kw FROM reports 
                    WHERE tc_name LIKE '%' || o.name || '%' AND is_short = 1 AND date(created_at) = ?
                    ORDER BY created_at DESC LIMIT 1) as load_power_kw
            FROM objects o
            LEFT JOIN reports r ON r.id = (
                SELECT id FROM reports 
                WHERE tc_name LIKE '%' || o.name || '%' AND date(created_at) = ?
                ORDER BY created_at DESC LIMIT 1
            )
            ORDER BY o.name
        """
        cursor = await db.execute(query, (today_str, today_str, today_str))
        rows = await cursor.fetchall()

        # Fetch all active shifts at once to map them efficiently
        shift_cursor = await db.execute("""
            SELECT s.object_id, u.full_name, u.phone_number 
            FROM shifts s 
            JOIN users u ON s.user_id = u.user_id 
            WHERE s.end_time IS NULL
        """)
        shift_rows = await shift_cursor.fetchall()
        active_shifts = {r['object_id']: (r['full_name'], r['phone_number']) for r in shift_rows}

        result = []
        for row in rows:
            d = dict(row)

            # Map shift info
            shift_info = active_shifts.get(d['id'])
            d['current_shift_name'] = shift_info[0] if shift_info else None
            d['current_shift_phone'] = shift_info[1] if shift_info else None

            name = d['name']

            short = name
            short = name
            if '(' in name and ')' in name:
                short = name.split('(')[1].split(')')[0]
            elif 'GPU' in name:
                short = name.split('GPU')[0].strip().split(' ')[-1]
            else:
                short = name.split(' ')[-1]
            d['short_name'] = short.replace('GPU', '').replace('ГПУ', '').strip()

            if not d['time_type']:
                st = (d['gpu_status'] or '').lower()
                d['time_type'] = 'start' if ('стабільна' in st or 'запуск' in st) else 'stop'

            s_cursor = await db.execute("SELECT schedule_json, is_not_working FROM trader_schedules WHERE object_id = ? AND target_date = ? LIMIT 1", (d['id'], today_str))
            s_row = await s_cursor.fetchone()
            try:
                d['current_schedule'] = json.loads(s_row[0]) if s_row and s_row[0] else []
                d['is_not_working'] = bool(s_row[1]) if s_row else False
            except Exception as e:
                logging.error(f"Error parsing schedule for object {d['id']}: {e}")
                d['current_schedule'] = []
                d['is_not_working'] = False
            result.append(d)
        return result

async def get_reports_by_date(date_str: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM reports WHERE date(created_at) = ? ORDER BY created_at DESC", (date_str,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_report_by_id(report_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def update_report_field(report_id: int, field_name: str, new_value: Any):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE reports SET {field_name} = ? WHERE id = ?", (new_value, report_id))
        await db.commit()

async def delete_report_by_id(report_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        await db.commit()

async def get_recent_reports(limit: int = 50, offset: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM reports ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_reports_by_range(start_date: str, end_date: str):
    """Returns reports between two dates for export."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Adding time to dates for full coverage
        query = "SELECT * FROM reports WHERE date(created_at) >= ? AND date(created_at) <= ? ORDER BY created_at ASC"
        cursor = await db.execute(query, (start_date, end_date))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

# --- User Functions ---

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_user_by_phone(phone_number: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE phone_number = ?", (phone_number,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def add_authorized_user(phone_number: str, full_name: str, role: str = 'user'):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO users (phone_number, full_name, role) VALUES (?, ?, ?) ON CONFLICT(phone_number) DO UPDATE SET full_name = EXCLUDED.full_name, role = EXCLUDED.role", (phone_number, full_name, role))
        await db.commit()

async def update_user_link(phone_number: str, user_id: int, username: Optional[str] = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET user_id = ?, username = ?, updated_at = CURRENT_TIMESTAMP WHERE phone_number = ?", (user_id, username, phone_number))
        await db.commit()

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT u.*, GROUP_CONCAT(o.name, '|') as object_names 
            FROM users u 
            LEFT JOIN user_objects uo ON u.id = uo.user_db_id 
            LEFT JOIN objects o ON uo.object_id = o.id 
            WHERE u.role = 'user' 
            GROUP BY u.id 
            ORDER BY u.full_name
        """)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_all_traders():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE role = 'trader' ORDER BY full_name")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def update_user_name(phone_number: str, new_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET full_name = ?, updated_at = CURRENT_TIMESTAMP WHERE phone_number = ?", (new_name, phone_number))
        await db.commit()

async def update_user_phone(user_id_db: int, new_phone: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET phone_number = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_phone, user_id_db))
        await db.commit()

async def get_user_by_db_id(user_id_db: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id_db,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def delete_user(phone_number: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users WHERE phone_number = ?", (phone_number,))
        await db.commit()

async def update_user_name_by_id(user_db_id: int, new_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET full_name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_name, user_db_id))
        await db.commit()

async def delete_user_by_id(user_db_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users WHERE id = ?", (user_db_id,))
        await db.commit()

async def add_or_update_user(user_id: int, full_name: str, username: Optional[str] = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, full_name, username)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET full_name = EXCLUDED.full_name, username = EXCLUDED.username, updated_at = CURRENT_TIMESTAMP
        """, (user_id, full_name, username))
        await db.commit()

# --- Object Functions ---

async def add_object(name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO objects (name) VALUES (?) ON CONFLICT(name) DO NOTHING", (name,))
        await db.commit()

async def get_all_objects():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM objects ORDER BY name")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_object_by_id(object_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM objects WHERE id = ?", (object_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def update_object_name(object_id: int, new_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE objects SET name = ? WHERE id = ?", (new_name, object_id))
        await db.commit()

async def delete_object_by_id(object_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM objects WHERE id = ?", (object_id,))
        await db.commit()

async def toggle_user_object_link(user_db_id: int, object_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM user_objects WHERE user_db_id = ? AND object_id = ?", (user_db_id, object_id))
        if await cursor.fetchone():
            await db.execute("DELETE FROM user_objects WHERE user_db_id = ? AND object_id = ?", (user_db_id, object_id))
        else:
            await db.execute("INSERT INTO user_objects (user_db_id, object_id) VALUES (?, ?)", (user_db_id, object_id))
        await db.commit()

async def get_user_objects(user_db_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT o.* FROM objects o JOIN user_objects uo ON o.id = uo.object_id WHERE uo.user_db_id = ? ORDER BY o.name", (user_db_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_user_objects_by_tg_id(user_tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT o.* FROM objects o 
            JOIN user_objects uo ON o.id = uo.object_id 
            JOIN users u ON u.id = uo.user_db_id 
            WHERE u.user_id = ? 
            ORDER BY o.name
        """, (user_tg_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_object_users(object_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT u.* FROM users u JOIN user_objects uo ON u.id = uo.user_db_id WHERE uo.object_id = ? ORDER BY u.full_name", (object_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

# --- Settings & Admin Functions ---

async def get_setting(key: str, default: str = "0"):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row[0] if row else default

async def update_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = EXCLUDED.value", (key, value))
        await db.commit()

# --- Web Auth Functions ---

async def save_web_auth_code(user_id: int, code: str, expires_at: datetime):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM web_auth_codes WHERE user_id = ?", (user_id,))
        await db.execute("INSERT INTO web_auth_codes (user_id, code, expires_at) VALUES (?, ?, ?)", (user_id, code, expires_at.strftime("%Y-%m-%d %H:%M:%S")))
        await db.commit()

async def get_web_auth_code(user_id: int, code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT * FROM web_auth_codes WHERE user_id = ? AND code = ? AND expires_at > ?", (user_id, code, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        return await cursor.fetchone() is not None

async def delete_web_auth_code(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM web_auth_codes WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_user_by_identifier(identifier: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if identifier.startswith('!'):
            try:
                cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (int(identifier[1:]),))
            except: return None
        else:
            cursor = await db.execute("SELECT * FROM users WHERE phone_number = ?", (identifier,))
        row = await cursor.fetchone()
        return dict(row) if row else None

# --- Trader & Schedule Functions ---

async def add_trader_schedule(object_id: int, trader_id: int, target_date: str, schedule_data: str, is_not_working: bool) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("INSERT INTO trader_schedules (object_id, trader_id, target_date, schedule_json, is_not_working) VALUES (?, ?, ?, ?, ?)", (object_id, trader_id, target_date, schedule_data, 1 if is_not_working else 0))
        last_id = cursor.lastrowid
        await db.commit()
        return last_id

async def get_schedule_by_id(schedule_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT s.*, o.name as tc_name, u.full_name as confirmed_user_name, o.telegram_group_id FROM trader_schedules s JOIN objects o ON s.object_id = o.id LEFT JOIN users u ON s.confirmed_by = u.id WHERE s.id = ?", (schedule_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def confirm_schedule(schedule_id: int, user_db_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE trader_schedules SET confirmed_by = ?, confirmed_at = CURRENT_TIMESTAMP WHERE id = ?", (user_db_id, schedule_id))
        await db.commit()

async def get_schedules_for_report(date_str: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT o.name as tc_name, o.telegram_group_id, s.id as schedule_id, s.is_not_working, s.confirmed_by, u.full_name as confirmed_user_name, s.confirmed_at FROM objects o LEFT JOIN trader_schedules s ON o.id = s.object_id AND s.target_date = ? LEFT JOIN users u ON s.confirmed_by = u.id ORDER BY o.name", (date_str,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def has_any_schedule(date_str: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM trader_schedules WHERE target_date = ? LIMIT 1", (date_str,))
        return await cursor.fetchone() is not None

# --- Trader Announcement Functions ---

async def add_trader_announcement(trader_id: int, target_date: str, chat_id: int, message_id: int, object_id: Optional[int] = None, message_type: str = 'announcement'):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO trader_announcements (trader_id, target_date, chat_id, message_id, object_id, message_type) VALUES (?, ?, ?, ?, ?, ?)", (trader_id, target_date, chat_id, message_id, object_id, message_type))
        await db.commit()

async def get_trader_announcements(trader_id: int, target_date: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM trader_announcements WHERE trader_id = ? AND target_date = ?", (trader_id, target_date))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def delete_trader_announcements_from_db(trader_id: int, target_date: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM trader_announcements WHERE trader_id = ? AND target_date = ?", (trader_id, target_date))
        await db.commit()

async def delete_schedules_by_date(trader_id: int, target_date: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM trader_schedules WHERE trader_id = ? AND target_date = ?", (trader_id, target_date))
        await db.commit()

# --- Group & Broadcast Management ---

async def add_telegram_group(tg_id: int, title: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO telegram_groups (tg_id, title) VALUES (?, ?) ON CONFLICT(tg_id) DO UPDATE SET title = EXCLUDED.title", (tg_id, title))
        await db.commit()

async def get_telegram_group(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM telegram_groups WHERE tg_id = ?", (tg_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_all_telegram_groups():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM telegram_groups ORDER BY title")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def link_group_to_object(object_id: int, tg_id: Optional[int]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE objects SET telegram_group_id = ? WHERE id = ?", (tg_id, object_id))
        await db.commit()

async def get_object_by_tg_group_id(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM objects WHERE telegram_group_id = ?", (tg_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_unlinked_groups():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT g.* FROM telegram_groups g LEFT JOIN objects o ON g.tg_id = o.telegram_group_id WHERE o.id IS NULL ORDER BY g.title")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def create_broadcast(admin_id: int, text: str, photo_id: Optional[str] = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("INSERT INTO broadcasts (admin_id, text, photo_id) VALUES (?, ?, ?)", (admin_id, text, photo_id))
        last_id = cursor.lastrowid
        await db.commit()
        return last_id

async def add_broadcast_message(broadcast_id: int, chat_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO broadcast_messages (broadcast_id, chat_id, message_id) VALUES (?, ?, ?)", (broadcast_id, chat_id, message_id))
        await db.commit()

async def get_broadcast(broadcast_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM broadcasts WHERE id = ?", (broadcast_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_broadcast_messages(broadcast_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM broadcast_messages WHERE broadcast_id = ?", (broadcast_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def update_broadcast_text(broadcast_id: int, new_text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE broadcasts SET text = ? WHERE id = ?", (new_text, broadcast_id))
        await db.commit()

async def update_broadcast_pin_status(broadcast_id: int, is_pinned: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE broadcast_messages SET is_pinned = ? WHERE broadcast_id = ?", (1 if is_pinned else 0, broadcast_id))
        await db.commit()

async def get_summary_data():
    """
    Извлекает данные для веб-отчетов. 
    Выбирает полные отчеты за сегодня с 01:00 (Киев).
    """
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo
    
    KYIV_TZ = ZoneInfo("Europe/Kiev")
    now_kiev = datetime.now(KYIV_TZ)
    today_str = now_kiev.strftime("%Y-%m-%d")
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # 1. Получаем все отчеты за сегодня и вчера (чтобы отфильтровать по Киевскому времени)
        query = """
            SELECT r.*, u.full_name as reported_by_name
            FROM reports r
            LEFT JOIN users u ON r.user_id = u.user_id
            WHERE r.battery_voltage IS NOT NULL 
            AND date(r.created_at) >= date('now', '-1 day')
            ORDER BY r.created_at DESC
        """
        cursor = await db.execute(query)
        rows = await cursor.fetchall()
        
        # 2. Получаем активные смены
        cursor = await db.execute("""
            SELECT s.object_id, u.full_name, u.phone_number 
            FROM shifts s 
            JOIN users u ON s.user_id = u.user_id 
            WHERE s.end_time IS NULL
        """)
        shift_rows = await cursor.fetchall()
        shifts = {r['object_id']: f"{r['full_name']} ({r['phone_number'] or '—'})" for r in shift_rows}
        
        # 3. Получаем маппинг объектов для сопоставления tc_name и object_id
        cursor = await db.execute("SELECT id, name FROM objects")
        obj_rows = await cursor.fetchall()
        obj_map = {r['name']: r['id'] for r in obj_rows}
        
        filtered_results = []
        seen_objects = set()
        
        for row in rows:
            d = dict(row)
            
            # Конвертируем создано_ат в Киев
            try:
                dt_utc = datetime.strptime(d['created_at'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except:
                dt_utc = datetime.fromisoformat(d['created_at'].replace('Z', '')).replace(tzinfo=timezone.utc)
                
            dt_kiev = dt_utc.astimezone(KYIV_TZ)
            
            # Фильтр: сегодня и время >= 01:00
            if dt_kiev.date() == now_kiev.date() and dt_kiev.hour >= 1:
                # Берем только самый свежий отчет для каждого объекта
                obj_name_full = d['tc_name']
                if obj_name_full in seen_objects:
                    continue
                seen_objects.add(obj_name_full)
                
                # Находим duty_info
                duty_info = "—"
                for name, oid in obj_map.items():
                    if name in obj_name_full:
                        duty_info = shifts.get(oid, "—")
                        break
                
                d['duty_info'] = duty_info
                d['created_at_kiev'] = dt_kiev.strftime("%H:%M")
                filtered_results.append(d)
                
        # Сортировка по имени объекта
        filtered_results.sort(key=lambda x: x['tc_name'])
        return filtered_results


async def delete_broadcast_from_db(broadcast_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM broadcasts WHERE id = ?", (broadcast_id,))
        await db.commit()

async def get_all_broadcasts(limit: int = 10, offset: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM broadcasts ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def count_broadcasts() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM broadcasts")
        row = await cursor.fetchone()
        return row[0] if row else 0

async def add_schedule_reminder(schedule_id: int, chat_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO schedule_reminders (schedule_id, chat_id, message_id) VALUES (?, ?, ?)", (schedule_id, chat_id, message_id))
        await db.commit()

async def get_schedule_reminders(schedule_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT chat_id, message_id FROM schedule_reminders WHERE schedule_id = ?", (schedule_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def delete_schedule_reminders_from_db(schedule_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM schedule_reminders WHERE schedule_id = ?", (schedule_id,))
        await db.commit()

# --- Web Push Notifications ---

async def add_push_subscription(user_id: int, subscription_json: str):
    """Saves a web push subscription for a user."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO web_push_subscriptions (user_id, subscription_json) VALUES (?, ?)",
            (user_id, subscription_json)
        )
        await db.commit()

async def get_all_push_subscriptions():
    """Returns all active web push subscriptions."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM web_push_subscriptions")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def remove_push_subscription(subscription_json: str):
    """Removes an invalid subscription."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM web_push_subscriptions WHERE subscription_json = ?", (subscription_json,))
        await db.commit()

# --- Schedule Event Reminders ---

async def was_reminder_sent(schedule_id: int, event_type: str, event_time: str) -> bool:
    """Checks if a reminder for a specific schedule event was already sent."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM schedule_event_reminders WHERE schedule_id = ? AND event_type = ? AND event_time = ?",
            (schedule_id, event_type, event_time)
        )
        return await cursor.fetchone() is not None

async def log_sent_reminder(schedule_id: int, event_type: str, event_time: str):
    """Logs that a reminder was sent."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO schedule_event_reminders (schedule_id, event_type, event_time) VALUES (?, ?, ?)",
            (schedule_id, event_type, event_time)
        )
        await db.commit()

async def check_report_exists(object_name: str, report_type: str, target_datetime: datetime) -> bool:
    """
    Checks if a report of a certain type (start/stop) exists for an object
    that was created around or after the target event time.
    target_datetime: event time in UTC.
    """
    # Look for reports created within a window: from 1 hour before event to now
    start_window = target_datetime - timedelta(hours=1)
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT 1 FROM reports 
            WHERE tc_name LIKE '%' || ? || '%' 
            AND time_type = ? 
            AND created_at >= ?
            LIMIT 1
            """,
            (object_name, report_type, start_window.strftime("%Y-%m-%d %H:%M:%S"))
        )
        return await cursor.fetchone() is not None

# --- Shift Management Functions ---

async def start_shift(user_id: int, object_id: int) -> int:
    """Starts a new shift for a user on a specific object."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO shifts (user_id, object_id, start_time) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (user_id, object_id)
        )
        shift_id = cursor.lastrowid
        await db.commit()
        return shift_id

async def end_shift(user_id: int, object_id: int, auto_closed: bool = False):
    """Ends the current active shift for a user on an object."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE shifts SET end_time = CURRENT_TIMESTAMP, auto_closed = ? WHERE user_id = ? AND object_id = ? AND end_time IS NULL",
            (1 if auto_closed else 0, user_id, object_id)
        )
        await db.commit()

async def get_active_shift(user_id: int, object_id: int):
    """Returns the current active shift for a user on an object."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM shifts WHERE user_id = ? AND object_id = ? AND end_time IS NULL LIMIT 1",
            (user_id, object_id)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_predecessor_shift(object_id: int, exclude_user_id: int):
    """Returns an active shift on the object belonging to someone else."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT s.*, u.full_name FROM shifts s JOIN users u ON s.user_id = u.user_id WHERE s.object_id = ? AND s.user_id != ? AND s.end_time IS NULL LIMIT 1",
            (object_id, exclude_user_id)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

async def set_planned_end_time(shift_id: int, planned_time: str):
    """Sets the planned end time for reminders."""
    # Convert HH:MM to full ISO string for today or tomorrow
    now = datetime.now()
    h, m = map(int, planned_time.split(':'))
    planned_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if planned_dt < now:
        planned_dt += timedelta(days=1)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE shifts SET planned_end_time = ? WHERE id = ?",
            (planned_dt.strftime("%Y-%m-%d %H:%M:%S"), shift_id)
        )
        await db.commit()

async def add_monthly_report(data: dict):
    """Saves a monthly GPU performance report to the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO monthly_reports (
                object_id, user_id, report_month, report_year, 
                energy_mwh, gas_start, gas_end, gas_coef, gas_total,
                oil_start, oil_end, oil_added, oil_total,
                spec_gas, spec_oil
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['object_id'], data['user_id'], data['report_month'], data['report_year'],
            data['energy_mwh'], data['gas_start'], data['gas_end'], data['gas_coef'], data['gas_total'],
            data['oil_start'], data['oil_end'], data['oil_added'], data['oil_total'],
            data['spec_gas'], data['spec_oil']
        ))
        await db.commit()
