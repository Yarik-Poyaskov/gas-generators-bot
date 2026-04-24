from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from datetime import datetime
import re

from app.config import config
from app.db.database import (
    get_user, get_schedule_by_id, confirm_schedule, get_object_users,
    get_schedule_reminders, delete_schedule_reminders_from_db
)

router = Router()

@router.callback_query(F.data.startswith("confirm_sched:"))
async def process_confirm_schedule_callback(callback: CallbackQuery, bot: Bot):
    schedule_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    now_time = datetime.now().strftime("%H:%M:%S")
    
    # 1. Получаем данные графика
    schedule = await get_schedule_by_id(schedule_id)
    if not schedule:
        await callback.answer("Графік не знайдено.")
        return

    # 2. Проверяем, не подтвержден ли он уже
    if schedule['confirmed_by']:
        await callback.answer(f"⚠️ Цей графік вже підтвердив {schedule['confirmed_user_name']}.", show_alert=True)
        # Если это группа, убираем кнопку, так как статус изменился
        if callback.message.chat.type in {"group", "supergroup"}:
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except: pass
        return

    # 3. Проверка прав доступа
    user_data = await get_user(user_id)
    if not user_data:
        await callback.answer("❌ Ви не зареєстровані в системі. Зверніться до адміна.", show_alert=True)
        return

    # Проверяем, привязан ли юзер к этому объекту
    from app.db.database import get_user_objects
    user_objs = await get_user_objects(user_data['id'])
    is_linked = any(obj['id'] == schedule['object_id'] for obj in user_objs)
    
    # Админы могут подтверждать всё
    if not is_linked and user_id not in config.admin_ids:
        await callback.answer("❌ Ви не закріплені за цим об'єктом.", show_alert=True)
        return

    # 4. Подтверждаем в базе
    await confirm_schedule(schedule_id, user_data['id'])
    
    # 5. Сообщаем пользователю об успехе
    await callback.answer("✅ Графік підтверджено!")
    
    # Очищаємо назву від дужок для повідомлення
    full_tc_name = schedule.get('tc_name', '')
    match_name = re.search(r'\((.*?)\)', full_tc_name)
    display_tc_name = match_name.group(1) if match_name else full_tc_name

    # 6. Обновляем сообщение (если это группа - убираем кнопку)
    if callback.message.chat.type in {"group", "supergroup"}:
        try:
            new_text = (
                f"{callback.message.text}\n\n"
                f"✅ <b>Підтвердив: {user_data['full_name']}</b>\n"
                f"<b>Час підтвердження: {now_time}</b>"
            )
            await callback.message.edit_text(text=new_text, reply_markup=None, parse_mode="HTML")
        except Exception as e:
            print(f"Помилка оновлення повідомлення в групі: {e}")
    else:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.message.answer(f"✅ Ви підтвердили цей графік о {now_time}.")

    # 7. Удаляем напоминания из группы
    reminders = await get_schedule_reminders(schedule_id)
    for r in reminders:
        try:
            await bot.delete_message(chat_id=r['chat_id'], message_id=r['message_id'])
        except Exception as e:
            # Може бути видалено вручну або минуло >48 год
            print(f"Помилка видалення нагадування: {e}")
    
    # Очищаємо базу від згадок про видалені нагадування
    await delete_schedule_reminders_from_db(schedule_id)

    # 8. Уведомляем Группу и других пользователей объекта
    notification_text = (
        f"✅ <b>ГРАФІК ПІДТВЕРДЖЕНО</b>\n\n"
        f"<b>Об'єкт:</b> {display_tc_name}\n"
        f"<b>На дату:</b> {schedule['target_date']}\n"
        f"<b>Підтвердив:</b> {user_data['full_name']}\n"
        f"<b>Час підтвердження:</b> {now_time}"
    )

    # В основную Группу (отчеты) - ТИМЧАСОВО ВИМКНЕНО
    # try:
    #     await bot.send_message(chat_id=config.group_id, text=notification_text)
    # except Exception as e:
    #     print(f"Помилка відправки в групу: {e}")

    # В тестовую Группу для разработчиков
    if config.test_special_group_id:
        try:
            await bot.send_message(chat_id=config.test_special_group_id, text=notification_text)
        except Exception as e:
            print(f"Помилка відправки в тестову групу: {e}")

    # Если есть локальная группа объекта - уведомляем и её
    linked_group_id = schedule.get('telegram_group_id')
    if linked_group_id:
        try:
            # Отправляем новое сообщение в локальную группу объекта
            sent_msg = await bot.send_message(chat_id=linked_group_id, text=notification_text, parse_mode="HTML")
            
            # ВАЖЛИВО: Зберігаємо ID цього повідомлення, щоб його можна було відкликати пізніше
            from app.db.database import add_trader_announcement
            # Шукаємо хто був трейдером для цього графіка
            trader_id = schedule.get('trader_id')
            if trader_id:
                await add_trader_announcement(
                    trader_id=trader_id, 
                    target_date=schedule['target_date'], 
                    chat_id=linked_group_id, 
                    message_id=sent_msg.message_id,
                    object_id=schedule['object_id'],
                    message_type='confirmation'
                )
        except Exception as e:
            print(f"Помилка відправки в локальну групу: {e}")

    # Всем пользователям этого объекта (в личку)
    obj_users = await get_object_users(schedule['object_id'])
    for u in obj_users:
        # Не шлем тому, кто только что нажал кнопку (ему мы уже ответили)
        if u['user_id'] and u['user_id'] != user_id:
            try:
                await bot.send_message(chat_id=u['user_id'], text=notification_text, parse_mode="HTML")
            except:
                pass
