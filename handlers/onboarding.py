import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from states import OnboardingState
from db import update_user, get_user
from keyboards.contact import get_contact_keyboard
from keyboards.subscription import get_subscription_keyboard
from texts import get_texts
from utils import track_message, delete_tracked_messages
import config
import app_state

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.in_({"lang_ru", "lang_uz"}))
async def choose_language(callback: CallbackQuery, state: FSMContext):
    lang = "ru" if callback.data == "lang_ru" else "uz"
    await update_user(callback.from_user.id, language=lang)
    t = get_texts(lang)

    await callback.message.delete()
    sent = await callback.message.answer(
        t.ASK_PHONE,
        reply_markup=get_contact_keyboard(t.BTN_SHARE_PHONE),
    )
    track_message(callback.from_user.id, sent.message_id)
    await state.set_state(OnboardingState.waiting_phone)
    await callback.answer()


@router.message(OnboardingState.waiting_phone, F.contact)
async def handle_phone(message: Message, state: FSMContext, texts):
    phone = message.contact.phone_number
    user_id = message.from_user.id
    await update_user(user_id, phone=phone)

    sent_ack = await message.answer("✅", reply_markup=ReplyKeyboardRemove())
    track_message(user_id, sent_ack.message_id)

    if not config.FREE_CHANNEL_ID:
        await state.clear()
        from handlers.content import send_welcome_and_video
        await send_welcome_and_video(message, texts)
    else:
        await state.set_state(OnboardingState.waiting_subscription)
        channel_url = f"https://t.me/{config.FREE_CHANNEL_ID.lstrip('@')}"
        sent_sub = await message.answer(
            texts.SUBSCRIBE_CHANNEL,
            reply_markup=get_subscription_keyboard(
                channel_link_text=texts.BTN_CHANNEL_LINK,
                channel_url=channel_url,
                check_text=texts.BTN_CHECK_SUB,
            ),
        )
        track_message(user_id, sent_sub.message_id)


@router.message(OnboardingState.waiting_phone)
async def handle_phone_wrong_format(message: Message, state: FSMContext, texts):
    sent = await message.answer(
        texts.ASK_PHONE,
        reply_markup=get_contact_keyboard(texts.BTN_SHARE_PHONE),
    )
    track_message(message.from_user.id, sent.message_id)


@router.callback_query(StateFilter(OnboardingState.waiting_subscription), F.data == "check_sub")
async def check_subscription(callback: CallbackQuery, state: FSMContext, texts):
    if not config.FREE_CHANNEL_ID:
        await state.clear()
        await callback.answer()
        await delete_tracked_messages(app_state.bot, callback.from_user.id)
        from handlers.content import send_welcome_and_video
        await send_welcome_and_video(callback.message, texts)
        return

    subscribed = False
    try:
        member = await callback.bot.get_chat_member(config.FREE_CHANNEL_ID, callback.from_user.id)
        subscribed = member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.warning(f"Cannot check subscription for {callback.from_user.id}: {e} — allowing through")
        subscribed = True

    if subscribed:
        await update_user(callback.from_user.id, is_subscribed=1)
        await state.clear()
        await callback.answer()
        await delete_tracked_messages(app_state.bot, callback.from_user.id)
        from handlers.content import send_welcome_and_video
        await send_welcome_and_video(callback.message, texts)
    else:
        await callback.answer(texts.NOT_SUBSCRIBED, show_alert=True)


@router.callback_query(F.data == "check_sub")
async def check_sub_fallback(callback: CallbackQuery):
    await callback.answer()
