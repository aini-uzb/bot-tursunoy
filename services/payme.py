import base64
import logging
import time
from aiohttp import web

from config import PAYME_MERCHANT_ID, PAYME_KEY, PAYME_URL

logger = logging.getLogger(__name__)

PENDING = 1
COMPLETED = 2
CANCELLED = -1
CANCELLED_AFTER_COMPLETE = -2


def generate_payme_url(order_id: int, amount_uzs: int, lang: str = "ru") -> str:
    amount_tiyin = amount_uzs * 100
    params = f"m={PAYME_MERCHANT_ID};ac.order_id={order_id};a={amount_tiyin};l={lang}"
    encoded = base64.b64encode(params.encode()).decode()
    return f"{PAYME_URL}/{encoded}"


async def payme_handler(request: web.Request) -> web.Response:
    auth = request.headers.get("Authorization", "")
    if not _check_auth(auth):
        return _error(-32504, "Insufficient privilege to perform this method")

    try:
        body = await request.json()
    except Exception:
        return _error(-32700, "Parse error")

    method = body.get("method")
    params = body.get("params", {})
    req_id = body.get("id", 1)

    logger.info(f"[Payme] {method}: {params}")

    handlers = {
        "CheckPerformTransaction": _check_perform,
        "CreateTransaction":       _create,
        "PerformTransaction":      _perform,
        "CancelTransaction":       _cancel,
        "CheckTransaction":        _check,
        "GetStatement":            _statement,
    }

    handler = handlers.get(method)
    if not handler:
        return _error(-32601, "Method not found", req_id)

    result = await handler(params)
    if "error" in result:
        return web.json_response({"id": req_id, "error": result["error"]})
    return web.json_response({"id": req_id, "result": result})


def _check_auth(auth_header: str) -> bool:
    try:
        encoded = auth_header.replace("Basic ", "")
        decoded = base64.b64decode(encoded).decode()
        login, password = decoded.split(":", 1)
        return login == "Paycom" and password == PAYME_KEY
    except Exception:
        return False


def _error(code: int, message: str, req_id=1) -> web.Response:
    return web.json_response({
        "id": req_id,
        "error": {"code": code, "message": {"ru": message, "uz": message, "en": message}},
    })


async def _check_perform(params: dict) -> dict:
    from db import get_payme_order
    account = params.get("account", {})
    order_id = account.get("order_id")
    amount = params.get("amount")

    try:
        order_id = int(order_id)
    except (TypeError, ValueError):
        return {"error": {"code": -31050, "message": {"ru": "Заказ не найден", "uz": "Buyurtma topilmadi", "en": "Order not found"}}}

    order = await get_payme_order(order_id)
    if not order:
        return {"error": {"code": -31050, "message": {"ru": "Заказ не найден", "uz": "Buyurtma topilmadi", "en": "Order not found"}}}
    if order["paid"]:
        return {"error": {"code": -31050, "message": {"ru": "Уже оплачено", "uz": "Allaqachon to'langan", "en": "Already paid"}}}
    if order["amount"] != int(amount):
        return {"error": {"code": -31001, "message": {"ru": "Неверная сумма", "uz": "Noto'g'ri summa", "en": "Wrong amount"}}}

    return {"allow": True}


async def _create(params: dict) -> dict:
    from db import (
        get_payme_order, save_payme_transaction, get_payme_transaction,
        get_payme_active_transaction_for_order,
    )
    transaction_id = params.get("id")
    account = params.get("account", {})
    order_id = account.get("order_id")
    amount = params.get("amount")

    try:
        order_id = int(order_id)
    except (TypeError, ValueError):
        return {"error": {"code": -31050, "message": {"ru": "Заказ не найден", "uz": "Buyurtma topilmadi", "en": "Order not found"}}}

    existing = await get_payme_transaction(transaction_id)
    if existing:
        return {
            "create_time": existing["create_time"],
            "transaction": transaction_id,
            "state": existing["state"],
        }

    order = await get_payme_order(order_id)
    if not order:
        return {"error": {"code": -31050, "message": {"ru": "Заказ не найден", "uz": "Buyurtma topilmadi", "en": "Order not found"}}}
    if order["amount"] != int(amount):
        return {"error": {"code": -31001, "message": {"ru": "Неверная сумма", "uz": "Noto'g'ri summa", "en": "Wrong amount"}}}

    # Order already has another active transaction → cannot create a second one
    active = await get_payme_active_transaction_for_order(order_id)
    if active:
        return {"error": {"code": -31050, "message": {"ru": "Заказ уже обрабатывается", "uz": "Buyurtma allaqachon ishlanmoqda", "en": "Order already in progress"}}}

    now = int(time.time() * 1000)
    await save_payme_transaction(transaction_id, order_id, int(amount), now)
    return {"create_time": now, "transaction": transaction_id, "state": PENDING}


async def _perform(params: dict) -> dict:
    from db import get_payme_transaction, complete_payme_transaction, mark_payme_order_paid, get_payme_order
    transaction_id = params.get("id")

    tx = await get_payme_transaction(transaction_id)
    if not tx:
        return {"error": {"code": -31003, "message": {"ru": "Транзакция не найдена", "uz": "Tranzaksiya topilmadi", "en": "Transaction not found"}}}

    if tx["state"] == COMPLETED:
        return {"transaction": transaction_id, "perform_time": tx["perform_time"], "state": COMPLETED}

    if tx["state"] != PENDING:
        return {"error": {"code": -31008, "message": {"ru": "Нельзя провести транзакцию", "uz": "Tranzaksiyani o'tkazib bo'lmaydi", "en": "Unable to perform"}}}

    now = int(time.time() * 1000)
    await complete_payme_transaction(transaction_id, now)
    await mark_payme_order_paid(tx["order_id"])

    order = await get_payme_order(tx["order_id"])
    if order:
        await _grant_access(order["user_id"], order["product_key"], tx["amount"])

    return {"transaction": transaction_id, "perform_time": now, "state": COMPLETED}


async def _cancel(params: dict) -> dict:
    from db import get_payme_transaction, cancel_payme_transaction
    transaction_id = params.get("id")
    reason = params.get("reason", 0)

    tx = await get_payme_transaction(transaction_id)
    if not tx:
        return {"error": {"code": -31003, "message": {"ru": "Транзакция не найдена", "uz": "Tranzaksiya topilmadi", "en": "Transaction not found"}}}

    # Already cancelled — idempotent, return existing cancel info
    if tx["state"] in (CANCELLED, CANCELLED_AFTER_COMPLETE):
        return {
            "transaction": transaction_id,
            "cancel_time": tx.get("cancel_time", 0),
            "state": tx["state"],
        }

    now = int(time.time() * 1000)
    # Pending → -1; completed → -2 (cancel after complete / refund)
    state = CANCELLED if tx["state"] == PENDING else CANCELLED_AFTER_COMPLETE
    await cancel_payme_transaction(transaction_id, state, reason, now)
    return {"transaction": transaction_id, "cancel_time": now, "state": state}


async def _check(params: dict) -> dict:
    from db import get_payme_transaction
    transaction_id = params.get("id")
    tx = await get_payme_transaction(transaction_id)
    if not tx:
        return {"error": {"code": -31003, "message": {"ru": "Транзакция не найдена", "uz": "Tranzaksiya topilmadi", "en": "Transaction not found"}}}

    return {
        "create_time":  tx.get("create_time", 0),
        "perform_time": tx.get("perform_time", 0),
        "cancel_time":  tx.get("cancel_time", 0),
        "transaction":  transaction_id,
        "state":        tx["state"],
        "reason":       tx.get("reason"),
    }


async def _statement(params: dict) -> dict:
    from db import get_payme_transactions_range
    from_ms = params.get("from", 0)
    to_ms = params.get("to", int(time.time() * 1000))
    rows = await get_payme_transactions_range(from_ms, to_ms)
    transactions = [
        {
            "id":           r["transaction_id"],
            "time":         r["create_time"],
            "amount":       r["amount"],
            "account":      {"order_id": str(r["order_id"])},
            "create_time":  r["create_time"],
            "perform_time": r["perform_time"],
            "cancel_time":  r["cancel_time"],
            "transaction":  r["transaction_id"],
            "state":        r["state"],
            "reason":       r.get("reason"),
        }
        for r in rows
    ]
    return {"transactions": transactions}


async def _grant_access(user_id: int, product_key: str, amount_tiyin: int):
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

        amount_uzs = amount_tiyin // 100
        await close_deal(
            user_data={"first_name": user.get("first_name", ""), "phone": user.get("phone", "")},
            product=course.get("name_ru", product_key),
            amount=amount_uzs,
        )

        admin_text = (
            f"✅ <b>Оплата получена (Payme)</b>\n\n"
            f"👤 {user.get('first_name', '')} (@{user.get('username', '') or '—'})\n"
            f"📞 {user.get('phone', '')}\n"
            f"📚 {course.get('name_ru', product_key)}\n"
            f"💰 {amount_uzs:,} сум"
        )
        await notify_admins(app_state.bot, admin_text)
