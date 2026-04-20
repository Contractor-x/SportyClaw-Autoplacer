import asyncio
import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler

from bot.commands import make_health_handler
from bot.listener import PHONE_NUMBER, get_client, message_betting_bot, register_handlers
from bot.reporter import fetch_account_summary, send_daily_report

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

daily_stats = {
    "placed": 0,
    "won": 0,
    "lost": 0,
    "ongoing": 0,
    "profit": 0.0,
    "loss": 0.0,
}


async def _scheduled_message_wrapper() -> None:
    try:
        await message_betting_bot()
    except Exception:
        logger.exception("Scheduled betting bot message failed.")


async def _scheduled_report_wrapper() -> None:
    try:
        await send_daily_report()
    except Exception:
        logger.exception("Scheduled daily report failed.")


def _start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Africa/Lagos")
    scheduler.add_job(
        _scheduled_message_wrapper,
        trigger="cron",
        hour=0,
        minute=0,
        id="scheduled-betting-bot-message-midnight",
        replace_existing=True,
    )
    scheduler.add_job(
        _scheduled_message_wrapper,
        trigger="cron",
        hour=12,
        minute=0,
        id="scheduled-betting-bot-message-noon",
        replace_existing=True,
    )
    scheduler.add_job(
        _scheduled_report_wrapper,
        trigger="cron",
        hour=8,
        minute=0,
        id="scheduled-daily-report",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started: message at 00:00 and 12:00, report at 08:00 (Africa/Lagos)")
    return scheduler


async def _warmup_account_fetch() -> None:
    try:
        await asyncio.to_thread(fetch_account_summary)
    except Exception:
        logger.exception("Warmup account summary fetch failed.")


def get_daily_stats() -> dict:
    return daily_stats


async def run() -> None:
    # Start Telethon client
    client = get_client()
    register_handlers(client)
    scheduler: AsyncIOScheduler | None = None
    bot_app: Application | None = None

    try:
        # Start Telethon
        if PHONE_NUMBER:
            await client.start(phone=PHONE_NUMBER)
        else:
            await client.start()
        logger.info("Telethon client started.")
        
        # Start Telegram Bot if BOT_TOKEN is configured
        if BOT_TOKEN:
            bot_app = Application.builder().token(BOT_TOKEN).build()
            bot_app.add_handler(CommandHandler("health", make_health_handler(get_daily_stats)))
            await bot_app.initialize()
            await bot_app.start()
            logger.info("Telegram bot started and /health command registered.")
            
            # Start polling in background
            asyncio.create_task(bot_app.updater.start_polling())
        else:
            logger.warning("BOT_TOKEN not set. Telegram bot /health command will not be available.")
        
        # Start scheduler
        scheduler = _start_scheduler()
        await _warmup_account_fetch()
        
        # Keep running
        await client.run_until_disconnected()
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)
        if bot_app:
            await bot_app.updater.stop()
            await bot_app.stop()
            await bot_app.shutdown()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
