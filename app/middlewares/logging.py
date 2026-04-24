import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

logger = logging.getLogger("UserActions")

class ActionLoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # В aiogram 3.x данные о пользователе передаются в словаре data автоматически
        user = data.get("event_from_user")
        
        if not user:
            return await handler(event, data)

        user_info = f"USER[ID:{user.id} | @{user.username or 'no_nick'} | {user.full_name}]"

        # Проверяем, что за событие пришло внутри Update
        if isinstance(event, Update):
            if event.message:
                msg = event.message
                if msg.text:
                    logger.info(f"{user_info} | TEXT: {msg.text}")
                elif msg.contact:
                    logger.info(f"{user_info} | CONTACT: {msg.contact.phone_number}")
                elif msg.photo:
                    logger.info(f"{user_info} | PHOTO SENT")
            
            elif event.callback_query:
                logger.info(f"{user_info} | BUTTON CLICKED: {event.callback_query.data}")

        return await handler(event, data)
