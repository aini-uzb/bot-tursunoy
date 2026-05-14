import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

from states import WarmupState
from db import get_user, update_user
from texts import get_texts
from utils import notify_admin
from services.crm import create_lead

router = Router()
logger = logging.getLogger(__name__)


async def warmup_job(user_id: int):
    """APScheduler callback — fires 30 min after video sent if user hasn't clicked watched."""
    import app_state

    user = await get_user(user_id)
    if not user:
        return
    if user.get("video_watched") or user.get("warmup_sent"):
        return

    bot = app_state.bot
    storage = app_state.storage
    t = get_texts(user.get("language", "ru"))

    key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
    state_ctx = FSMContext(storage=storage, key=key)
    await state_ctx.set_state(WarmupState.question_1)

    await bot.send_message(user_id, t.WARMUP_INVITE)
    await bot.send_message(user_id, t.WARMUP_Q1)
    await update_user(user_id, warmup_sent=1)
    logger.info(f"Warmup sent to user {user_id}")

    # Второй таймер — если проигнорировал вопросы (ещё +30 мин)
    from datetime import datetime, timedelta
    app_state.scheduler.add_job(
        warmup_silent_job,
        "date",
        run_date=datetime.now() + timedelta(minutes=30),
        id=f"warmup_silent_{user_id}",
        kwargs={"user_id": user_id},
        replace_existing=True,
    )


async def warmup_silent_job(user_id: int):
    """Fires 30 min after warmup if user still hasn't answered."""
    import app_state

    user = await get_user(user_id)
    if not user:
        return
    if user.get("warmup_answer_1") or user.get("video_watched"):
        return

    t = get_texts(user.get("language", "ru"))
    try:
        await app_state.bot.send_message(user_id, t.WARMUP_SILENT)
        logger.info(f"Silent warmup sent to user {user_id}")
    except Exception as e:
        logger.warning(f"Silent warmup failed for {user_id}: {e}")
        return

    # Отправляем лид в CRM — только телефон и username
    await create_lead({
        "user_id": user_id,
        "first_name": user.get("first_name", ""),
        "username": user.get("username", ""),
        "phone": user.get("phone", ""),
        "type": "silent_warmup",
    })

    # Уведомляем админа
    username = user.get("username", "")
    phone = user.get("phone", "")
    admin_text = (
        "⏰ <b>Молчаливый лид</b>\n\n"
        f"👤 {user.get('first_name', '')} (@{username or '—'})\n"
        f"📞 {phone or '—'}\n\n"
        "Не ответил на вопросы догрева. Можно написать вручную."
    )
    await notify_admin(app_state.bot, admin_text)


@router.message(WarmupState.question_1)
async def warmup_q1_answer(message: Message, state: FSMContext, texts):
    await update_user(message.from_user.id, warmup_answer_1=message.text)
    await state.set_state(WarmupState.question_2)
    await message.answer(texts.WARMUP_Q2)


@router.message(WarmupState.question_2)
async def warmup_q2_answer(message: Message, state: FSMContext, texts):
    answer_2 = message.text
    await update_user(message.from_user.id, warmup_answer_2=answer_2)
    await state.clear()
    await message.answer(texts.WARMUP_THANKS)

    user = await get_user(message.from_user.id)
    if not user:
        return

    # CRM
    await create_lead({
        "user_id": message.from_user.id,
        "first_name": user.get("first_name", ""),
        "username": user.get("username", ""),
        "phone": user.get("phone", ""),
        "answer_1": user.get("warmup_answer_1", ""),
        "answer_2": answer_2,
    })

    # Notify admin
    import app_state
    admin_text = texts.ADMIN_WARMUP_LEAD.format(
        first_name=user.get("first_name", ""),
        username=user.get("username", "") or "нет",
        phone=user.get("phone", ""),
        answer_1=user.get("warmup_answer_1", ""),
        answer_2=answer_2,
    )
    await notify_admin(app_state.bot, admin_text)
