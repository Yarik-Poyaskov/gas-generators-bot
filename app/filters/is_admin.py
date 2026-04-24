from aiogram.filters import BaseFilter
from aiogram.types import Message
from typing import Union

from app.config import config

class IsAdmin(BaseFilter):
    """
    Custom filter to check if a user is an admin.
    """
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in config.admin_ids
