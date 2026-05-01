import asyncio
import aiosqlite
import logging
from playwright.async_api import async_playwright
from aiogram import Bot
from aiogram.types import FSInputFile
import os
import re
from datetime import datetime, timedelta, timezone
from app.config import config
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# --- НАЛАШТУВАННЯ ЧАСУ ЗВІТУ ---
REPORT_START_HOUR = 1   # 01:00 ночі
REPORT_END_HOUR = 9     # до 09:00
REPORT_END_MINUTE = 30  # і 30 хвилин
# -------------------------------

DB_PATH = "reports.db"
KYIV_TZ = ZoneInfo("Europe/Kiev")
logger = logging.getLogger(__name__)

def get_report_period_str():
    """Повертає рядок періоду для заголовків."""
    return f"{REPORT_START_HOUR:02d}:00 - {REPORT_END_HOUR:02d}:{REPORT_END_MINUTE:02d}"

async def get_active_shifts_dict():
    """Повертає словник {object_id: 'ПІБ (телефон)'} для активних змін."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT s.object_id, u.full_name, u.phone_number 
            FROM shifts s 
            JOIN users u ON s.user_id = u.user_id 
            WHERE s.end_time IS NULL
        """
        cursor = await db.execute(query)
        rows = await cursor.fetchall()
        
        shifts = {}
        for r in rows:
            phone = r['phone_number'] or "—"
            shifts[r['object_id']] = f"{r['full_name']} ({phone})"
        return shifts

async def get_objects_mapping():
    """Повертає мапінг {object_name: object_id}."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT id, name FROM objects")
        rows = await cursor.fetchall()
        return {r['name']: r['id'] for r in rows}

async def get_today_full_reports():
    """Извлекает ПОВНЫЕ отчеты, ПОДАННЫЕ сегодня в заданный период по Киеву."""
    now = datetime.now(KYIV_TZ)
    start_minutes = REPORT_START_HOUR * 60
    end_minutes = REPORT_END_HOUR * 60 + REPORT_END_MINUTE

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        query = "SELECT * FROM reports WHERE battery_voltage IS NOT NULL AND date(created_at) >= date('now', '-1 day')"
        cursor = await db.execute(query)
        rows = await cursor.fetchall()

        filtered_reports = []
        for row in rows:
            created_at_str = row['created_at']
            try:
                dt_utc = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except:
                dt_utc = datetime.fromisoformat(created_at_str.replace('Z', '')).replace(tzinfo=timezone.utc)

            local_created = dt_utc.astimezone(KYIV_TZ)

            if local_created.date() == now.date():
                time_in_minutes = local_created.hour * 60 + local_created.minute
                if start_minutes <= time_in_minutes <= end_minutes:
                    filtered_reports.append(dict(row))

        filtered_reports.sort(key=lambda x: x['tc_name'])
        return filtered_reports

def format_html_table(reports, shifts, obj_map):
    """Создает HTML для сводной таблицы с информацией о дежурных."""
    rows_html = ""
    period_str = get_report_period_str()
    for idx, r in enumerate(reports, 1):
        gpu_status = r.get('gpu_status') or "—"
        status_style = "status-ok" if "Стабільна" in gpu_status else "status-err"
        
        full_name = r.get('tc_name') or "Невідомий об'єкт"
        match_name = re.search(r'\((.*?)\)', full_name)
        display_name = match_name.group(1) if match_name else full_name

        # Find shift info
        obj_id = None
        for name, oid in obj_map.items():
            if name in full_name:
                obj_id = oid
                break
        
        duty_info = shifts.get(obj_id, "—")

        s_time = r.get('start_time') or "—"
        if "Плановий - " in s_time:
            s_time = s_time.replace("Плановий - ", "")
        
        load_pct = r.get('load_power_percent') or "0"
        load_kw = r.get('load_power_kw') or "0"
        work_mode = r.get('work_mode') or "—"

        rows_html += f"""
        <tr>
            <td style="text-align: center; color: #9aa0a6; font-weight: bold; width: 30px;">{idx}</td>
            <td>{display_name}</td>
            <td>{work_mode}</td>
            <td>{s_time}</td>
            <td>{load_pct}% / {load_kw} кВт</td>
            <td><span class="{status_style}">{gpu_status}</span></td>
            <td>{duty_info}</td>
        </tr>
        """
    
    return f"""
    <!DOCTYPE html>
    <html lang="uk">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background: #f0f2f5; padding: 20px; }}
            .container {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 25px rgba(0,0,0,0.1); width: 1100px; margin: auto; border-top: 10px solid #1a73e8; }}
            h2 {{ text-align: center; color: #1a73e8; margin-bottom: 5px; text-transform: uppercase; }}
            h3 {{ text-align: center; color: #5f6368; font-weight: normal; margin-bottom: 30px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ background: #f8f9fa; color: #5f6368; font-weight: 600; text-align: left; padding: 12px; border-bottom: 2px solid #dee2e6; font-size: 13px; }}
            td {{ padding: 12px; border-bottom: 1px solid #eee; color: #3c4043; font-size: 13px; }}
            tr:nth-child(even) {{ background: #fafafa; }}
            tr:hover {{ background: #f1f3f4; }}
            .status-ok {{ color: #1e8e3e; background: #e6f4ea; padding: 4px 10px; border-radius: 20px; font-weight: bold; font-size: 11px; }}
            .status-err {{ color: #d93025; background: #fce8e6; padding: 4px 10px; border-radius: 20px; font-weight: bold; font-size: 11px; }}
            .footer {{ text-align: right; margin-top: 25px; font-size: 11px; color: #9aa0a6; border-top: 1px solid #eee; padding-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Зведенний звіт по ГПУ (З черговими)</h2>
            <h3>Період подачі: {period_str}</h3>
            <table>
                <thead>
                    <tr>
                        <th style="text-align: center; width: 30px;">№</th>
                        <th>Об'єкт</th>
                        <th>Режим</th>
                        <th>Час запуску</th>
                        <th>Потужність</th>
                        <th>Статус</th>
                        <th>Черговий (Телефон)</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
            <div class="footer">Дата: {datetime.now(KYIV_TZ).strftime("%d.%m.%Y")} | Згенеровано: {datetime.now(KYIV_TZ).strftime("%H:%M")}</div>
        </div>
    </body>
    </html>
    """

async def run_summary_report(bot: Bot, target_chat_id: int = None):
    """Основна функція для запуску зведеного звіту (тепер з черговими)."""
    now_kiev = datetime.now(KYIV_TZ)
    period_str = get_report_period_str()
    logger.info("🚀 Запуск генерації зведеного звіту (з черговими)...")
    
    reports = await get_today_full_reports()
    shifts = await get_active_shifts_dict()
    obj_map = await get_objects_mapping()
    
    if not reports:
        msg = f"ℹ️ Звітів за період {period_str} не знайдено."
        if target_chat_id:
            await bot.send_message(chat_id=target_chat_id, text=msg)
        return

    html_content = format_html_table(reports, shifts, obj_map)
    
    if not os.path.exists('tmp'):
        os.makedirs('tmp')
    
    output_path = os.path.join('tmp', f"summary_{now_kiev.strftime('%Y%m%d_%H%M%S')}.png")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_viewport_size({"width": 1200, "height": 1000})
            await page.set_content(html_content)
            await asyncio.sleep(1)
            element = await page.query_selector(".container")
            if element:
                await element.screenshot(path=output_path)
            else:
                await page.screenshot(path=output_path)
            await browser.close()

    except Exception as e:
        logger.error(f"Error during Playwright: {e}")

    if os.path.exists(output_path):
        photo = FSInputFile(output_path)
        caption = f"📋 Зведенний звіт (ЧЕРГОВІ)\n📅 {now_kiev.strftime('%d.%m.%Y')}\n⏰ Період: {period_str}"
        
        chat_id = target_chat_id or config.special_group_id

        if chat_id:
            try:
                await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption)
                print(f"[{now_kiev.strftime('%H:%M:%S')}] ✅ Звіт (з черговими) надіслано в чат {chat_id}")
            except Exception as e:
                logger.error(f"Error sending photo to {chat_id}: {e}")

if __name__ == "__main__":
    async def test_run():
        bot = Bot(token=config.bot_token.get_secret_value())
        await run_summary_report(bot)
        await bot.session.close()
    asyncio.run(test_run())
