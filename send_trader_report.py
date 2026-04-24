import asyncio
import re
from aiogram import Bot
from datetime import datetime
import os

from app.config import config
from app.db.database import get_schedules_for_report

async def send_trader_status_report():
    """Генерирует текстовый отчет о статусе поданных графиков на сегодня."""
    today_db_str = datetime.now().strftime("%Y-%m-%d")
    today_display_str = datetime.now().strftime("%d.%m.%Y")

    # Получаем данные из БД
    schedules = await get_schedules_for_report(today_db_str)

    # Оставляем только те, где график подан (есть schedule_id)
    submitted_schedules = [s for s in schedules if s['schedule_id']]

    if not submitted_schedules:
        print(f"ℹ️ На {today_display_str} ще не подано жодного графіка.")
        return

    report_text = f"📊 <b>СТАТУС ПОДАНИХ ГРАФІКІВ</b>\n"
    report_text += f"📅 Дата: {today_display_str}\n"
    report_text += f"⏰ Час звіту: {datetime.now().strftime('%H:%M')}\n\n"

    for s in submitted_schedules:
        # Shorten object name (remove parentheses)
        full_tc_name = s.get('tc_name', '')
        match_name = re.search(r'\((.*?)\)', full_tc_name)
        display_tc_name = match_name.group(1) if match_name else full_tc_name

        status_icon = "✅" if s['confirmed_by'] else "⏳"
        confirmed_info = f"\n   └ Підтвердив: {s['confirmed_user_name']}" if s['confirmed_by'] else "\n   └ <b>ОЧІКУЄ ПІДТВЕРДЖЕННЯ</b>"
        work_status = "НЕ ПРАЦЮЄ" if s['is_not_working'] else "Є ГРАФІК"
        report_text += f"{status_icon} <b>{display_tc_name}</b>: {work_status}{confirmed_info}\n\n"

    # Отправляем в SPECIAL_GROUP_ID
    chat_id = config.test_special_group_id
    if chat_id:
        try:
            # Добавлена поддержка HTML тегов (parse_mode)
            await bot.send_message(chat_id=chat_id, text=report_text, parse_mode="HTML")
            print("🚀 Отчет по поданным графикам отправлен.")
        except Exception as e:
            print(f"Помилка відправки звіту: {e}")
    else:
        print("❌ SPECIAL_GROUP_ID не настроен.")

if __name__ == "__main__":
    async def test_run():
        bot = Bot(token=config.bot_token.get_secret_value())
        await run_trader_report(bot)
        await bot.session.close()
    
    asyncio.run(test_run())
