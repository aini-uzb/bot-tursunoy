from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from texts import get_texts
from db import get_user


class I18nMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user:
            user_data = await get_user(user.id)
            lang = user_data.get("language", "ru") if user_data else "ru"
            data["texts"] = get_texts(lang)
        else:
            data["texts"] = get_texts("ru")
        return await handler(event, data)
