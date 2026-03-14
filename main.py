import logging
import os
import asyncio
from datetime import time as dtime
from reporter import send_daily_report
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
from bot.commands import make_health_handler
from health import start_health_server

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
REPORT_TIME = os.getenv("REPORT_TIME", "23:00")  # 24hr format, WAT (UTC+1)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# In-memory daily stats — resets on each deploy/restart
daily_stats = {
    "placed": 0,
    "won": 0,
    "lost": 0,
    "ongoing": 0,
    "profit": 0.0,
    "loss": 0.0,
}


def reset_daily_stats():
    global daily_stats
    daily_stats = {
        "placed": 0,
        "won": 0,
        "lost": 0,
        "ongoing": 0,
        "profit": 0.0,
        "loss": 0.0,
    }


def parse_report_time() -> dtime:
    hour, minute = REPORT_TIME.strip().split(":")
    return dtime(int(hour), int(minute), 0)


def get_daily_stats() -> dict:
    return daily_stats


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set.")

    start_health_server()

    report_time = parse_report_time()
    logger.info(f"Daily report scheduled at {REPORT_TIME} WAT")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Schedule daily report job
    app.job_queue.run_daily(
        callback=lambda ctx: asyncio.ensure_future(send_daily_report()),
        time=report_time,
        name="daily_report",
    )

    # Schedule daily stats reset at midnight
    app.job_queue.run_daily(
        callback=lambda ctx: reset_daily_stats(),
        time=dtime(0, 0, 0),
        name="daily_reset",
    )

    from bot.listener import handle_message
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("health", make_health_handler(get_daily_stats)))

    logger.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
