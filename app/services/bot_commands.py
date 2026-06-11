import aiosqlite
import logging
from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from app.config import config

DB_PATH = "reports.db"

async def set_user_menu_commands(bot: Bot, user_id: int, is_admin: bool, role: str):
    """Встановлює персональне меню команд Telegram для конкретного користувача (тільки в ЛС)."""
    commands = [
        BotCommand(command="start", description="🏠 Головне меню / Перезапуск"),
    ]
    
    if role == 'trader':
        commands.append(BotCommand(command="trader_schedule", description="📅 Подати графік роботи ГПУ"))
    elif role == 'user':
        commands.append(BotCommand(command="report", description="📝 Подати повний чек-лист"))
        commands.append(BotCommand(command="status", description="⚡ Короткий статус ГПУ"))
        commands.append(BotCommand(command="shifts", description="👤 Керування змінами"))
        commands.append(BotCommand(command="monthly_diff", description="📊 Звіт за місяць (різниця)"))
        commands.append(BotCommand(command="monthly_corr", description="📊 Звіт за місяць (коректор)"))

    if is_admin:
        # Для адміна з роллю, що відрізняється від user/trader, також додамо чек-листи
        if role != 'user' and role != 'trader':
            commands.append(BotCommand(command="report", description="📝 Подати повний чек-лист"))
            commands.append(BotCommand(command="status", description="⚡ Короткий статус ГПУ"))
            commands.append(BotCommand(command="shifts", description="👤 Керування змінами"))
            commands.append(BotCommand(command="monthly_diff", description="📊 Звіт за місяць (різниця)"))
            commands.append(BotCommand(command="monthly_corr", description="📊 Звіт за місяць (коректор)"))
        
        commands.append(BotCommand(command="trader_schedule", description="📅 Подати графік роботи ГПУ"))
        commands.append(BotCommand(command="admin", description="⚙️ Адмін панель"))

    commands.append(BotCommand(command="cancel", description="❌ Скасувати поточну дію"))

    try:
        await bot.set_my_commands(
            commands=commands,
            scope=BotCommandScopeChat(chat_id=user_id)
        )
    except Exception as e:
        logging.error(f"Не вдалося встановити меню команд для користувача {user_id}: {e}")

async def initialize_all_user_commands(bot: Bot):
    """Масово налаштовує меню команд для всіх зареєстрованих користувачів та адміністраторів."""
    logging.info("👥 Початок масової ініціалізації меню команд для користувачів...")
    
    # 0. Очищуємо дефолтне меню для груп (робимо його пустим)
    try:
        await bot.delete_my_commands(scope=BotCommandScopeDefault())
        logging.info("🧹 Глобальне дефолтне меню команд очищено (це приховує меню в групах).")
    except Exception as e:
        logging.error(f"Помилка при очищенні дефолтного меню команд: {e}")

    # 1. Зчитуємо користувачів з БД
    users = []
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT user_id, role FROM users WHERE user_id IS NOT NULL") as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    users.append({
                        'user_id': row['user_id'],
                        'role': row['role']
                    })
    except Exception as e:
        logging.error(f"Помилка при зчитуванні користувачів для меню команд: {e}")
        return

    admin_ids = config.admin_ids or []
    processed_ids = set()
    
    # 2. Оновлюємо меню для користувачів з БД
    for u in users:
        uid = u['user_id']
        role = u['role']
        is_admin = uid in admin_ids
        await set_user_menu_commands(bot, uid, is_admin, role)
        processed_ids.add(uid)
        
    # 3. Додаємо адміністраторів, яких може не бути в БД (прописані в .env)
    for aid in admin_ids:
        if aid not in processed_ids:
            await set_user_menu_commands(bot, aid, is_admin=True, role='user')
            processed_ids.add(aid)
            
    logging.info(f"👥 Масова ініціалізація меню команд завершена. Оновлено меню для {len(processed_ids)} користувачів.")
