import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter, Command

from config import ADMIN_IDS, COURSES, CHANNEL_SUBSCRIPTION
from db import get_pending_payment, update_payment, get_admin_messages, get_user, get_stats
from keyboards.products import get_admin_payment_keyboard
from states import AdminState
from services.subscription import grant_access
from services.crm import close_deal
import app_state
import texts.ru as ru_texts

router = Router()
logger = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("setvideo"))
async def setvideo_command(message: Message):
    """Reply to a video message with /setvideo to get its file_id."""
    if not _is_admin(message.from_user.id):
        return
    reply = message.reply_to_message
    if not reply or not reply.video:
        await message.answer(
            "Ответьте командой /setvideo на сообщение с видео.\n\n"
            "Перешлите видео в этот чат → ответьте на него /setvideo"
        )
        return
    file_id = reply.video.file_id
    await message.answer(
        f"✅ <b>file_id видео:</b>\n<code>{file_id}</code>\n\n"
        f"Скопируй и поставь на Railway как переменную:\n"
        f"<code>VIDEO_FILE_ID={file_id}</code>"
    )


@router.message(Command("stats"))
async def stats_command(message: Message):
    if not _is_admin(message.from_user.id):
        return

    now = datetime.now()
    all_time = await get_stats()
    last_month = await get_stats(since=now - timedelta(days=30))
    last_year = await get_stats(since=now - timedelta(days=365))

    def fmt(s: dict) -> str:
        return (
            f"👥 Начали бот: <b>{s['starts']}</b>\n"
            f"💳 Перешли к оплате: <b>{s['payment_views']}</b>\n"
            f"✅ Оплатили: <b>{s['paid']}</b>"
            + (f" (вручную: {s['manual_paid']}, Payme: {s['payme_paid']})" if s['paid'] else "")
        )

    text = (
        "📊 <b>Статистика бота</b>\n\n"
        "📅 <b>За всё время:</b>\n"
        f"{fmt(all_time)}\n\n"
        "📅 <b>За последние 30 дней:</b>\n"
        f"{fmt(last_month)}\n\n"
        "📅 <b>За последний год:</b>\n"
        f"{fmt(last_year)}"
    )
    await message.answer(text)


async def _edit_all_admin_messages(payment_id: int, new_caption: str):
    """Remove buttons from all admin messages and append result text."""
    admin_msgs = await get_admin_messages(payment_id)
    payment = await get_pending_payment(payment_id)
    if not payment:
        return
    original_caption = payment.get("photo_file_id", "")  # we use caption from payment check

    for admin_id_str, msg_id in admin_msgs.items():
        try:
            await app_state.bot.edit_message_caption(
                chat_id=int(admin_id_str),
                message_id=msg_id,
                caption=new_caption,
                reply_markup=None,
            )
        except Exception as e:
            logger.warning(f"Could not edit admin message for {admin_id_str}: {e}")


@router.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    payment_id = int(callback.data.removeprefix("approve_"))
    payment = await get_pending_payment(payment_id)

    if not payment:
        await callback.answer("Платёж не найден", show_alert=True)
        return

    if payment["status"] != "pending":
        await callback.answer(ru_texts.ADMIN_ALREADY_PROCESSED, show_alert=True)
        return

    await update_payment(payment_id, status="approved", processed_by=callback.from_user.id)

    user = await get_user(payment["user_id"])
    product_key = payment["product_key"]
    course = COURSES.get(product_key) or (CHANNEL_SUBSCRIPTION if product_key == "channel_sub" else None)

    # Grant access: add user to channel and get invite link
    invite_link = await grant_access(
        user_id=payment["user_id"],
        product_key=product_key,
    )

    # Close deal in CRM
    if user and course:
        await close_deal(
            user_data={
                "first_name": user.get("first_name", ""),
                "username": user.get("username", ""),
                "phone": user.get("phone", ""),
            },
            product=course.get("name_ru", product_key),
            amount=course.get("price", 0),
        )

    # Notify user
    if user and course:
        lang = user.get("language", "ru")
        import texts.ru as ru_t
        import texts.uz as uz_t
        t = uz_t if lang == "uz" else ru_t
        await app_state.bot.send_message(payment["user_id"], t.ACCESS_GRANTED)
        link = invite_link or "— ссылка будет добавлена —"
        await app_state.bot.send_message(payment["user_id"], link)

    # Update all admin messages
    admin_username = callback.from_user.username or str(callback.from_user.id)
    new_caption = (
        ru_texts.ADMIN_PAYMENT_CHECK.format(
            payment_id=payment_id,
            first_name=user.get("first_name", "") if user else "",
            username=user.get("username", "") or "нет" if user else "нет",
            phone=user.get("phone", "") if user else "",
            course_name=course["name_ru"] if course else payment["product_key"],
            price=course["price"] if course else "—",
        )
        + f"\n\n{ru_texts.ADMIN_PAYMENT_APPROVED.format(admin_username=admin_username)}"
    )
    await _edit_all_admin_messages(payment_id, new_caption)
    await callback.answer("✅ Подтверждено!")
    logger.info(f"Payment #{payment_id} approved by admin {callback.from_user.id}")


@router.callback_query(F.data.startswith("decline_"))
async def start_decline(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    payment_id = int(callback.data.removeprefix("decline_"))
    payment = await get_pending_payment(payment_id)

    if not payment:
        await callback.answer("Платёж не найден", show_alert=True)
        return

    if payment["status"] != "pending":
        await callback.answer(ru_texts.ADMIN_ALREADY_PROCESSED, show_alert=True)
        return

    await state.set_state(AdminState.entering_decline_reason)
    await state.update_data(payment_id=payment_id)
    await callback.message.answer(
        ru_texts.ADMIN_ASK_DECLINE_REASON.format(payment_id=payment_id)
    )
    await callback.answer()


@router.message(StateFilter(AdminState.entering_decline_reason))
async def process_decline_reason(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        await state.clear()
        return

    data = await state.get_data()
    payment_id = data.get("payment_id")
    await state.clear()

    if not payment_id:
        return

    payment = await get_pending_payment(payment_id)
    if not payment or payment["status"] != "pending":
        await message.answer(ru_texts.ADMIN_ALREADY_PROCESSED)
        return

    reason = message.text.strip()
    await update_payment(payment_id, status="declined", processed_by=message.from_user.id, decline_reason=reason)

    # Notify user
    user = await get_user(payment["user_id"])
    if user:
        lang = user.get("language", "ru")
        import texts.ru as ru_t
        import texts.uz as uz_t
        t = uz_t if lang == "uz" else ru_t
        await app_state.bot.send_message(
            payment["user_id"],
            t.PAYMENT_DECLINED.format(reason=reason),
        )

    # Update all admin messages
    course = COURSES.get(payment["product_key"])
    admin_username = message.from_user.username or str(message.from_user.id)
    new_caption = (
        ru_texts.ADMIN_PAYMENT_CHECK.format(
            payment_id=payment_id,
            first_name=user.get("first_name", "") if user else "",
            username=user.get("username", "") or "нет" if user else "нет",
            phone=user.get("phone", "") if user else "",
            course_name=course["name_ru"] if course else payment["product_key"],
            price=course["price"] if course else "—",
        )
        + f"\n\n{ru_texts.ADMIN_PAYMENT_DECLINED.format(admin_username=admin_username, reason=reason)}"
    )
    await _edit_all_admin_messages(payment_id, new_caption)
    await message.answer(f"✅ Платёж #{payment_id} отклонён.")
    logger.info(f"Payment #{payment_id} declined by admin {message.from_user.id}: {reason}")
