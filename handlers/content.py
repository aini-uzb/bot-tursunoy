import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from config import VIDEO_FILE_ID
from db import update_user
from keyboards.video import get_video_keyboard
from keyboards.products import get_category_keyboard
from utils import track_message, delete_tracked_messages

router = Router()
logger = logging.getLogger(__name__)


async def send_welcome_and_video(message: Message, texts):
    """Steps 4+5: welcome text → video (or placeholder) with warmup timer."""
    user_id = message.from_user.id
    if VIDEO_FILE_ID:
        sent_video = await message.answer_video(
            video=VIDEO_FILE_ID,
            caption=texts.VIDEO_MESSAGE,
            reply_markup=get_video_keyboard(texts.BTN_WATCHED),
        )
    else:
        sent_video = await message.answer(
            texts.WELCOME + "\n\n" + texts.VIDEO_PLACEHOLDER,
            reply_markup=get_video_keyboard(texts.BTN_WATCHED),
        )
    track_message(user_id, sent_video.message_id)

    now = datetime.now()
    await update_user(user_id, video_sent_at=now.isoformat())
    _schedule_warmup(user_id, now)


def _schedule_warmup(user_id: int, now: datetime):
    import app_state
    from handlers.warmup import warmup_job

    job_id = f"warmup_{user_id}"
    try:
        app_state.scheduler.remove_job(job_id)
    except Exception:
        pass

    app_state.scheduler.add_job(
        warmup_job,
        "date",
        run_date=now + timedelta(minutes=30),
        id=job_id,
        kwargs={"user_id": user_id},
    )
    logger.info(f"Warmup scheduled for user {user_id} in 30 min")


@router.callback_query(F.data == "video_watched")
async def handle_video_watched(callback: CallbackQuery, texts):
    user_id = callback.from_user.id

    import app_state
    from db import get_user

    # Убираем кнопку сразу — защита от двойного нажатия
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    user = await get_user(user_id)
    await update_user(user_id, video_watched=1)

    try:
        app_state.scheduler.remove_job(f"warmup_{user_id}")
        logger.info(f"Warmup job cancelled for user {user_id}")
    except Exception:
        pass

    lang = user.get("language", "ru") if user else "ru"

    await delete_tracked_messages(app_state.bot, user_id)
    await callback.message.answer(
        texts.PRODUCTS_INTRO,
        reply_markup=get_category_keyboard(lang),
    )
    await callback.answer()
