import logging
import config
import app_state

logger = logging.getLogger(__name__)


def track_message(user_id: int, message_id: int):
    """Remember a message ID so it can be bulk-deleted later."""
    app_state.user_messages.setdefault(user_id, []).append(message_id)


async def delete_tracked_messages(bot, user_id: int):
    """Delete all tracked messages for a user."""
    msg_ids = app_state.user_messages.pop(user_id, [])
    for msg_id in msg_ids:
        try:
            await bot.delete_message(user_id, msg_id)
        except Exception:
            pass


async def notify_admins(bot, text: str, **kwargs):
    """Send text to all configured admin IDs. Falls back to log if none configured."""
    if not config.ADMIN_IDS:
        logger.info(f"[ADMIN] {text}")
        return
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, parse_mode="HTML", **kwargs)
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")


# Keep old name as alias so existing callers don't break
async def notify_admin(bot, text: str, **kwargs):
    await notify_admins(bot, text, **kwargs)
