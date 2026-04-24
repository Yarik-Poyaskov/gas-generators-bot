from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from app.config import config
from app.db.database import add_telegram_group, get_telegram_group

router = Router()

# Filter for groups and supergroups only
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

@router.message(Command("init"))
async def cmd_init_group(message: Message):
    # Only allow ADMIN_IDS to initialize groups
    if message.from_user.id not in config.admin_ids:
        return

    group_id = message.chat.id
    group_title = message.chat.title
    
    existing = await get_telegram_group(group_id)
    if existing:
        await message.answer(f"⚠️ Ця група вже зареєстрована як: <b>{existing['title']}</b>")
        return

    await add_telegram_group(group_id, group_title)
    await message.answer(
        f"✅ <b>Групу успішно зареєстровано!</b>\n\n"
        f"Назва: {group_title}\n"
        f"ID: <code>{group_id}</code>\n\n"
        "Тепер ви можете прив'язати її до об'єкта в адмін-панелі бота."
    )

@router.message(Command("init_force"))
async def cmd_init_group_force(message: Message):
    # Only allow ADMIN_IDS to initialize groups
    if message.from_user.id not in config.admin_ids:
        return

    group_id = message.chat.id
    group_title = message.chat.title
    
    await add_telegram_group(group_id, group_title)
    await message.answer(
        f"🔄 <b>Дані групи оновлено (примусово)!</b>\n\n"
        f"Назва: {group_title}\n"
        f"ID: <code>{group_id}</code>"
    )
