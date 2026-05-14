"""
amoCRM v4 integration.

Setup (one-time):
1. Go to https://ttprogresscom.amocrm.ru/settings/oauth/
2. Create integration → get client_id, client_secret, redirect_uri
3. Fill them in .env: AMOCRM_CLIENT_ID, AMOCRM_CLIENT_SECRET, AMOCRM_REDIRECT_URI
4. Run: python setup_crm.py  → follow browser link → paste code → tokens saved to crm_tokens.json
"""
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp

from config import AMOCRM_DOMAIN, AMOCRM_CLIENT_ID, AMOCRM_CLIENT_SECRET, AMOCRM_REDIRECT_URI

logger = logging.getLogger(__name__)
TOKENS_FILE = Path("crm_tokens.json")


def _load_tokens() -> dict:
    if TOKENS_FILE.exists():
        try:
            return json.loads(TOKENS_FILE.read_text())
        except Exception:
            pass
    return {
        "access_token": os.getenv("AMOCRM_ACCESS_TOKEN", ""),
        "refresh_token": os.getenv("AMOCRM_REFRESH_TOKEN", ""),
        "expires_at": "",
    }


def _save_tokens(tokens: dict):
    TOKENS_FILE.write_text(json.dumps(tokens, indent=2))


async def _refresh_access_token() -> str | None:
    """Exchange refresh_token for a new access_token."""
    tokens = _load_tokens()
    refresh_token = tokens.get("refresh_token", "")
    if not refresh_token or not AMOCRM_CLIENT_ID:
        logger.warning("[CRM] No refresh_token or client_id — CRM disabled")
        return None

    url = f"https://{AMOCRM_DOMAIN}/oauth2/access_token"
    payload = {
        "client_id": AMOCRM_CLIENT_ID,
        "client_secret": AMOCRM_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "redirect_uri": AMOCRM_REDIRECT_URI,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                if "access_token" in data:
                    expires_at = (datetime.now() + timedelta(seconds=data.get("expires_in", 86400))).isoformat()
                    _save_tokens({
                        "access_token": data["access_token"],
                        "refresh_token": data.get("refresh_token", refresh_token),
                        "expires_at": expires_at,
                    })
                    logger.info("[CRM] Tokens refreshed")
                    return data["access_token"]
                else:
                    logger.error(f"[CRM] Token refresh failed: {data}")
    except Exception as e:
        logger.error(f"[CRM] Token refresh error: {e}")
    return None


async def _get_token() -> str | None:
    tokens = _load_tokens()
    access_token = tokens.get("access_token", "")
    if not access_token:
        return await _refresh_access_token()

    expires_at = tokens.get("expires_at", "")
    if expires_at:
        try:
            if datetime.fromisoformat(expires_at) < datetime.now() + timedelta(minutes=5):
                return await _refresh_access_token()
        except ValueError:
            pass
    return access_token


async def _post(endpoint: str, payload: list | dict) -> dict | None:
    if not AMOCRM_DOMAIN:
        logger.info(f"[CRM] (no domain) {endpoint}: {payload}")
        return None

    token = await _get_token()
    if not token:
        logger.info(f"[CRM] (no token) {endpoint}: {payload}")
        return None

    url = f"https://{AMOCRM_DOMAIN}/api/v4/{endpoint}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                result = await resp.json()
                logger.info(f"[CRM] {endpoint} → {resp.status}")
                return result
    except Exception as e:
        logger.error(f"[CRM] Request error {endpoint}: {e}")
        return None


async def create_lead(user_data: dict):
    """Create contact + lead in amoCRM."""
    logger.info(f"[CRM] New lead: {user_data}")

    phone = user_data.get("phone", "")
    username = user_data.get("username", "")
    user_id = user_data.get("user_id", "")
    first_name = user_data.get("first_name", "Без имени")
    lead_type = user_data.get("type", "lead")
    course = user_data.get("course", "")

    # Имя контакта с Telegram username если есть
    contact_name = first_name
    if username:
        contact_name = f"{first_name} (@{username})"

    # Create contact
    contact_payload = [{
        "first_name": contact_name,
        "custom_fields_values": [
            {"field_code": "PHONE", "values": [{"value": phone, "enum_code": "WORK"}]}
        ] if phone else [],
    }]
    contact_result = await _post("contacts", contact_payload)

    contact_id = None
    if contact_result:
        try:
            contact_id = contact_result["_embedded"]["contacts"][0]["id"]
        except (KeyError, IndexError, TypeError):
            pass

    # Название лида — из чего пришёл
    if course:
        lead_name = f"📚 {course}"
    elif lead_type in ("consult", "consult_answers"):
        lead_name = "🎯 Консультация (Telegram)"
    else:
        lead_name = "🤖 Лид из Telegram-бота"

    tg_note = f"Telegram ID: {user_id}"
    if username:
        tg_note += f"\nUsername: @{username}"

    lead_payload = [{
        "name": lead_name,
        "pipeline_id": 8189886,
        "status_id": 66927334,  # Взято в обработку
        "tags_to_add": [{"name": "Telegram"}],
        "_embedded": {},
    }]
    if contact_id:
        lead_payload[0]["_embedded"]["contacts"] = [{"id": contact_id}]

    lead_result = await _post("leads", lead_payload)

    # Добавляем примечание с Telegram данными
    if lead_result and user_id:
        try:
            lead_id = lead_result["_embedded"]["leads"][0]["id"]
            note_payload = [{"entity_id": lead_id, "note_type": "common", "params": {"text": tg_note}}]
            await _post(f"leads/{lead_id}/notes", note_payload)
        except (KeyError, IndexError, TypeError):
            pass


async def close_deal(user_data: dict, product: str, amount: int):
    """Move lead to Won in amoCRM."""
    logger.info(f"[CRM] Deal closed: {user_data} | {product} | ${amount}")
    lead_payload = [{
        "name": f"✅ {product}",
        "pipeline_id": 8189886,
        "status_id": 142,  # Успешно реализовано (Won)
        "price": amount,
        "tags_to_add": [{"name": "Telegram"}, {"name": "Оплачено"}],
    }]
    await _post("leads", lead_payload)
