import logging
from datetime import datetime, timedelta

from config import COURSES, CHANNEL_SUBSCRIPTION
from db import create_subscription, get_expiring_soon, get_expired, mark_warned, delete_subscription, get_user
from texts import get_texts

logger = logging.getLogger(__name__)


async def grant_access(user_id: int, product_key: str) -> str | None:
    """Add user to the course channel, record subscription, return invite link."""
    import app_state

    course = COURSES.get(product_key) or (CHANNEL_SUBSCRIPTION if product_key == "channel_sub" else None)
    if not course:
        logger.error(f"Unknown product_key: {product_key}")
        return None

    channel_id = course.get("channel_id", "")
    if not channel_id:
        logger.warning(f"No channel_id configured for {product_key} — skipping add")
        return None

    days = course["days"]
    expires_at = datetime.now() + timedelta(days=days)

    # Create invite link (single-use)
    invite_link = None
    try:
        link_obj = await app_state.bot.create_chat_invite_link(
            chat_id=channel_id,
            member_limit=1,
            expire_date=int(expires_at.timestamp()),
        )
        invite_link = link_obj.invite_link
        logger.info(f"Invite link created for user {user_id} → {channel_id}")
    except Exception as e:
        logger.error(f"Failed to create invite link for {channel_id}: {e}")

    # Record subscription so scheduler can kick later
    await create_subscription(user_id, product_key, channel_id, expires_at)
    logger.info(f"Subscription created: user={user_id} course={product_key} expires={expires_at.date()}")

    return invite_link


async def check_subscriptions_job():
    """APScheduler daily job: warn 1 day before expiry, kick on expiry."""
    import app_state

    # Warn users expiring within 24 hours
    expiring = await get_expiring_soon(hours_ahead=24)
    for sub in expiring:
        user = await get_user(sub["user_id"])
        pk = sub["product_key"]
        course = COURSES.get(pk) or (CHANNEL_SUBSCRIPTION if pk == "channel_sub" else None)
        if not user or not course:
            await mark_warned(sub["id"])
            continue
        lang = user.get("language", "ru")
        t = get_texts(lang)
        course_name = course["name_ru"] if lang == "ru" else course["name_uz"]
        try:
            await app_state.bot.send_message(
                sub["user_id"],
                t.SUB_EXPIRY_WARNING.format(course_name=course_name),
            )
        except Exception as e:
            logger.warning(f"Could not warn user {sub['user_id']}: {e}")
        await mark_warned(sub["id"])
        logger.info(f"Expiry warning sent to user {sub['user_id']} for {sub['product_key']}")

    # Kick expired users
    expired = await get_expired()
    for sub in expired:
        user = await get_user(sub["user_id"])
        pk2 = sub["product_key"]
        course = COURSES.get(pk2) or (CHANNEL_SUBSCRIPTION if pk2 == "channel_sub" else None)
        channel_id = sub["channel_id"]

        # Kick from channel
        try:
            await app_state.bot.ban_chat_member(channel_id, sub["user_id"])
            await app_state.bot.unban_chat_member(channel_id, sub["user_id"])
            logger.info(f"Kicked user {sub['user_id']} from {channel_id}")
        except Exception as e:
            logger.warning(f"Could not kick user {sub['user_id']} from {channel_id}: {e}")

        # Notify user
        if user and course:
            lang = user.get("language", "ru")
            t = get_texts(lang)
            course_name = course["name_ru"] if lang == "ru" else course["name_uz"]
            try:
                await app_state.bot.send_message(
                    sub["user_id"],
                    t.SUB_EXPIRED.format(course_name=course_name),
                )
            except Exception as e:
                logger.warning(f"Could not notify expired user {sub['user_id']}: {e}")

        await delete_subscription(sub["id"])
