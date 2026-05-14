"""
Handles bot being added/removed as admin in channels.
Fires when bot status changes in any chat — notifies admins with channel ID.
"""
import logging
from aiogram import Router, F
from aiogram.types import ChatMemberUpdated

from utils import notify_admins
import app_state

router = Router()
logger = logging.getLogger(__name__)


@router.my_chat_member()
async def bot_status_changed(event: ChatMemberUpdated):
    """Fires on ANY bot membership change in a chat/channel."""
    new_status = event.new_chat_member.status  # administrator, member, kicked, left, etc.

    if new_status != "administrator":
        return  # only care when bot becomes admin

    chat = event.chat
    msg = (
        f"✅ <b>Бот стал администратором</b>\n\n"
        f"📢 Название: <b>{chat.title}</b>\n"
        f"🆔 Chat ID: <code>{chat.id}</code>\n"
        f"🔗 Username: @{chat.username or '—'}\n\n"
        f"Вставь в .env нужную строку (замени XXX на название курса):\n"
        f"<code>CHANNEL_XXX={chat.id}</code>"
    )
    await notify_admins(app_state.bot, msg)
    logger.info(f"Bot became admin in '{chat.title}' id={chat.id}")
