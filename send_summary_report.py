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
# Тут ви можете легко змінити період подачі звітів
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

def format_html_table(reports):
    """Создает HTML для сводной таблицы."""
    rows_html = ""
    period_str = get_report_period_str()
    for r in reports:
        gpu_status = r.get('gpu_status') or "—"
        status_style = "status-ok" if "Стабільна" in gpu_status else "status-err"
        
        full_name = r.get('tc_name') or "Невідомий об'єкт"
        match_name = re.search(r'\((.*?)\)', full_name)
        display_name = match_name.group(1) if match_name else full_name

        s_time = r.get('start_time') or "—"
        if "Плановий - " in s_time:
            s_time = s_time.replace("Плановий - ", "")
        
        load_pct = r.get('load_power_percent') or "0"
        load_kw = r.get('load_power_kw') or "0"
        total_mwh = r.get('total_mwh') or "0"
        total_hours = r.get('total_hours') or "0"
        work_mode = r.get('work_mode') or "—"

        rows_html += f"""
        <tr>
            <td>{display_name}</td>
            <td>{work_mode}</td>
            <td>{s_time}</td>
            <td>{load_pct}% / {load_kw} кВт</td>
            <td><span class="{status_style}">{gpu_status}</span></td>
            <td>{total_mwh}</td>
            <td>{total_hours}</td>
        </tr>
        """
    
    return f"""
    <!DOCTYPE html>
    <html lang="uk">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background: #f0f2f5; padding: 20px; }}
            .container {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 25px rgba(0,0,0,0.1); width: 1000px; margin: auto; border-top: 10px solid #1a73e8; }}
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
            <h2>Зведенний звіт по ГПУ</h2>
            <h3>Період подачі: {period_str} (Повні звіти)</h3>
            <table>
                <thead>
                    <tr>
                        <th>Об'єкт</th>
                        <th>Режим</th>
                        <th>Час запуску</th>
                        <th>Потужність</th>
                        <th>Статус</th>
                        <th>МВт*год</th>
                        <th>м/год</th>
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
    """Основная функция для запуска по расписанию или по запросу."""
    now_kiev = datetime.now(KYIV_TZ)
    period_str = get_report_period_str()
    logger.info("🚀 Запуск генерації зведеного звіту...")
    
    reports = await get_today_full_reports()
    logger.info(f"📊 Знайдено повних звітів: {len(reports)}")
    
    if not reports:
        msg = f"ℹ️ Звітів за період {period_str} не знайдено."
        if target_chat_id:
            await bot.send_message(chat_id=target_chat_id, text=msg)
        logger.info(msg)
        return

    html_content = format_html_table(reports)
    
    if not os.path.exists('tmp'):
        os.makedirs('tmp')
    
    output_path = os.path.join('tmp', f"summary_{now_kiev.strftime('%Y%m%d_%H%M%S')}.png")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_viewport_size({"width": 1100, "height": 1000})
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
        caption = f"📋 Зведенний звіт (ПОВНИЙ)\n📅 {now_kiev.strftime('%d.%m.%Y')}\n⏰ Період подачі: {period_str}"
        
        # Если указан конкретный чат (запрос от админа)
        if target_chat_id:
            await bot.send_photo(chat_id=target_chat_id, photo=photo, caption=caption)
            print(f"[{now_kiev.strftime('%H:%M:%S')}] ✅ Звіт надіслано в чат {target_chat_id} (за запитом)")
            return

        # Логика для рассылки по умолчанию
        chat_id = config.special_group_id
        if not chat_id:
            from dotenv import load_dotenv
            load_dotenv()
            chat_id_env = os.getenv("SPECIAL_GROUP_ID")
            if chat_id_env: chat_id = int(chat_id_env)

        if chat_id:
            await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption)
            print(f"[{now_kiev.strftime('%H:%M:%S')}] 🚀 Сводный отчет отправлен в {chat_id}")

if __name__ == "__main__":
    async def test_run():
        bot = Bot(token=config.bot_token.get_secret_value())
        await run_summary_report(bot)
        await bot.session.close()
    asyncio.run(test_run())
