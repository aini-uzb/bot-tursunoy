import logging

logger = logging.getLogger(__name__)


async def create_payment(amount: int, description: str) -> str:
    """Заглушка Payme/Click — возвращает фейковую ссылку"""
    logger.info(f"[PAYMENT] Создан платёж: {amount} сум — {description}")
    # TODO: интеграция с Payme/Click API
    return "https://payme.uz/placeholder"
