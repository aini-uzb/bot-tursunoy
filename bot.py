import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web

from config import BOT_TOKEN, ADMIN_IDS
from db import init_db
from middleware.i18n import I18nMiddleware
from handlers import start, onboarding, content, products, warmup
from handlers import admin as admin_handler
from handlers import broadcast as broadcast_handler
from handlers import channel_events
import app_state

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def click_prepare_handler(request: web.Request) -> web.Response:
    try:
        data = dict(await request.post())
        logger.info(f"[Click] /prepare received: {data}")
        from services.click import handle_prepare
        result = await handle_prepare(data)
        return web.json_response(result)
    except Exception as e:
        logger.exception(f"[Click] /prepare error: {e}")
        return web.json_response({"error": -9, "error_note": "Internal error"})


async def click_complete_handler(request: web.Request) -> web.Response:
    try:
        data = dict(await request.post())
        logger.info(f"[Click] /complete received: {data}")
        from services.click import handle_complete
        result = await handle_complete(data)
        return web.json_response(result)
    except Exception as e:
        logger.exception(f"[Click] /complete error: {e}")
        return web.json_response({"error": -9, "error_note": "Internal error"})


async def health_handler(_: web.Request) -> web.Response:
    return web.Response(text="OK")


def build_web_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/click/prepare", click_prepare_handler)
    app.router.add_post("/click/complete", click_complete_handler)
    # GET нужен чтобы Click мог проверить URL при сохранении в кабинете
    app.router.add_get("/click/prepare", health_handler)
    app.router.add_get("/click/complete", health_handler)
    app.router.add_get("/health", health_handler)
    return app


async def main():
    storage = MemoryStorage()
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    app_state.bot = bot
    app_state.storage = storage
    app_state.scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
    app_state.admin_ids = ADMIN_IDS

    dp = Dispatcher(storage=storage)

    dp.message.middleware(I18nMiddleware())
    dp.callback_query.middleware(I18nMiddleware())

    # Routers in priority order
    dp.include_router(start.router)
    dp.include_router(onboarding.router)
    dp.include_router(content.router)
    dp.include_router(products.router)
    dp.include_router(admin_handler.router)
    dp.include_router(warmup.router)
    dp.include_router(broadcast_handler.router)  # channel_post handler
    dp.include_router(channel_events.router)     # bot promoted to admin in channel

    await init_db()

    # Daily subscription expiry check at 09:00 Tashkent
    from services.subscription import check_subscriptions_job
    app_state.scheduler.add_job(
        check_subscriptions_job,
        "cron",
        hour=9,
        minute=0,
        id="subscription_daily_check",
        replace_existing=True,
    )

    app_state.scheduler.start()

    # Start aiohttp server for Click webhooks
    port = int(os.getenv("PORT", "8080"))
    web_app = build_web_app()
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Click webhook server started on port {port}")

    logger.info("Bot started")
    try:
        await dp.start_polling(
            bot,
            allowed_updates=["message", "callback_query", "channel_post", "my_chat_member"],
        )
    finally:
        await runner.cleanup()
        app_state.scheduler.shutdown(wait=False)
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
