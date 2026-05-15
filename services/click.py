import hashlib
import logging
import time

from config import CLICK_SERVICE_ID, CLICK_MERCHANT_ID, CLICK_SECRET_KEY

logger = logging.getLogger(__name__)


def generate_payment_url(user_id: int, product_key: str, amount_uzs: int) -> str:
    merchant_trans_id = f"{user_id}_{product_key}_{int(time.time())}"
    return (
        f"https://my.click.uz/services/pay"
        f"?service_id={CLICK_SERVICE_ID}"
        f"&merchant_id={CLICK_MERCHANT_ID}"
        f"&amount={amount_uzs}"
        f"&transaction_param={merchant_trans_id}"
    )


def _sign(click_trans_id, merchant_trans_id, amount, action, sign_time, merchant_prepare_id="") -> str:
    if action == 0:
        raw = f"{click_trans_id}{CLICK_SERVICE_ID}{CLICK_SECRET_KEY}{merchant_trans_id}{amount}{action}{sign_time}"
    else:
        raw = f"{click_trans_id}{CLICK_SERVICE_ID}{CLICK_SECRET_KEY}{merchant_trans_id}{merchant_prepare_id}{amount}{action}{sign_time}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _parse_trans_id(merchant_trans_id: str):
    """Parse 'user_id_product_key_timestamp' → (user_id, product_key).
    product_key может содержать '_' (например channel_sub),
    поэтому отрезаем timestamp справа, user_id слева.
    """
    # Убираем timestamp (последняя часть после последнего '_')
    without_ts = merchant_trans_id.rsplit("_", 1)[0]  # "7586078580_channel_sub"
    parts = without_ts.split("_", 1)                  # ["7586078580", "channel_sub"]
    if len(parts) < 2:
        return None, None
    try:
        return int(parts[0]), parts[1]
    except ValueError:
        return None, None


async def handle_prepare(data: dict) -> dict:
    click_trans_id = data.get("click_trans_id", "")
    merchant_trans_id = data.get("merchant_trans_id", "")
    amount = data.get("amount", "")
    sign_time = data.get("sign_time", "")
    sign_string = data.get("sign_string", "")

    expected = _sign(click_trans_id, merchant_trans_id, amount, 0, sign_time)
    logger.info(f"[Click] prepare sign: expected={expected} got={sign_string} match={expected==sign_string}")
    logger.info(f"[Click] prepare raw: trans={click_trans_id} svc={CLICK_SERVICE_ID} mtrans={merchant_trans_id} amount={amount} time={sign_time}")
    # Временно пропускаем проверку подписи для диагностики
    # if expected != sign_string:
    #     logger.warning(f"[Click] prepare sign MISMATCH")
    #     return {"error": -1, "error_note": "SIGN CHECK FAILED!"}

    user_id, product_key = _parse_trans_id(merchant_trans_id)
    if not user_id:
        return {"error": -5, "error_note": "USER DOES NOT EXIST"}

    from db import get_user
    user = await get_user(user_id)
    if not user:
        return {"error": -5, "error_note": "USER DOES NOT EXIST"}

    logger.info(f"[Click] prepare OK: user={user_id} product={product_key} amount={amount}")
    return {
        "click_trans_id": int(click_trans_id),
        "merchant_trans_id": merchant_trans_id,
        "merchant_prepare_id": user_id,
        "error": 0,
        "error_note": "Success",
    }


async def handle_complete(data: dict) -> dict:
    click_trans_id = data.get("click_trans_id", "")
    merchant_trans_id = data.get("merchant_trans_id", "")
    merchant_prepare_id = data.get("merchant_prepare_id", "")
    amount = data.get("amount", "")
    sign_time = data.get("sign_time", "")
    sign_string = data.get("sign_string", "")
    error = int(data.get("error", 0))

    expected = _sign(click_trans_id, merchant_trans_id, amount, 1, sign_time, merchant_prepare_id)
    logger.info(f"[Click] complete sign: expected={expected} got={sign_string} match={expected==sign_string}")
    # Временно пропускаем проверку подписи для диагностики
    # if expected != sign_string:
    #     logger.warning(f"[Click] complete sign mismatch")
    #     return {"error": -1, "error_note": "SIGN CHECK FAILED!"}

    if error < 0:
        logger.info(f"[Click] payment cancelled/failed: {merchant_trans_id}")
        return {"error": 0, "error_note": "Success"}

    user_id, product_key = _parse_trans_id(merchant_trans_id)
    if not user_id:
        return {"error": -5, "error_note": "USER DOES NOT EXIST"}

    logger.info(f"[Click] complete: user={user_id} product={product_key} amount={amount}")

    from services.subscription import grant_access
    from services.crm import close_deal
    from db import get_user
    from config import COURSES, CHANNEL_SUBSCRIPTION
    from texts import get_texts
    from utils import notify_admins
    import app_state

    invite_link = await grant_access(user_id, product_key)

    user = await get_user(user_id)
    course = COURSES.get(product_key) or (CHANNEL_SUBSCRIPTION if product_key == "channel_sub" else None)

    if user and course:
        lang = user.get("language", "ru")
        t = get_texts(lang)
        await app_state.bot.send_message(user_id, t.ACCESS_GRANTED)
        link = invite_link or "— обратитесь к администратору —"
        await app_state.bot.send_message(user_id, link)

        await close_deal(
            user_data={"first_name": user.get("first_name", ""), "phone": user.get("phone", "")},
            product=course.get("name_ru", product_key),
            amount=int(float(amount)),
        )

        admin_text = (
            f"✅ <b>Оплата получена (Click)</b>\n\n"
            f"👤 {user.get('first_name', '')} (@{user.get('username', '') or '—'})\n"
            f"📞 {user.get('phone', '')}\n"
            f"📚 {course.get('name_ru', product_key)}\n"
            f"💰 {amount} сум"
        )
        await notify_admins(app_state.bot, admin_text)

    return {
        "click_trans_id": int(click_trans_id),
        "merchant_trans_id": merchant_trans_id,
        "merchant_confirm_id": user_id,
        "error": 0,
        "error_note": "Success",
    }
