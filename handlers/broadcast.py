import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

from config import BROADCAST_HASHTAGS
from db import get_all_user_ids
import app_state

router = Router()
logger = logging.getLogger(__name__)


def _has_broadcast_hashtag(text: str) -> bool:
    """True if the post contains AT LEAST ONE broadcast tag.

    This is a yes/no check, not a counter — a post with several tags
    (e.g. #поступление #admission #qabul) still triggers exactly one
    forward per user below. No duplicates from multiple tags.
    """
    if not text:
        return False
    text_lower = text.lower()
    return any(tag.lower() in text_lower for tag in BROADCAST_HASHTAGS)


async def _user_is_in_fsm(user_id: int) -> bool:
    """Return True if user has an active FSM state (mid-conversation)."""
    key = StorageKey(bot_id=app_state.bot.id, chat_id=user_id, user_id=user_id)
    state_ctx = FSMContext(storage=app_state.storage, key=key)
    current = await state_ctx.get_state()
    return current is not None


@router.channel_post()
async def on_channel_post(message: Message):
    """Triggered when a post appears in any channel the bot is in."""
    text = message.text or message.caption or ""
    if not _has_broadcast_hashtag(text):
        return

    logger.info(f"Broadcast triggered by post {message.message_id} in {message.chat.id}")

    user_ids = await get_all_user_ids()
    sent = 0
    skipped = 0

    for user_id in user_ids:
        # Skip users mid-conversation so we don't interrupt them
        if await _user_is_in_fsm(user_id):
            skipped += 1
            continue
        try:
            await message.forward(chat_id=user_id)
            sent += 1
        except Exception as e:
            logger.debug(f"Broadcast skip user {user_id}: {e}")

    logger.info(f"Broadcast done: sent={sent}, skipped_fsm={skipped}")
