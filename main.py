import logging
import os
import asyncio
from datetime import time as dtime
import reporter
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
from bot.commands import make_health_handler
from health import start_health_server
from bankroll import initialize_from_amount, parse_balance, reset as reset_bankroll

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
REPORT_TIME = os.getenv("REPORT_TIME", "23:00")  # 24hr format, WAT (UTC+1)
MAX_BETS_PER_DAY = int(os.getenv("MAX_BETS_PER_DAY", "30"))

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


def sync_refresh_bankroll():
    try:
        account = reporter.fetch_account_summary()
        balance = parse_balance(account.get("balance"))
        initialize_from_amount(balance, max_bets_per_day=MAX_BETS_PER_DAY)
    except Exception as exc:
        logger.exception("Failed to refresh bankroll: %s", exc)


async def refresh_bankroll_async():
    await asyncio.to_thread(sync_refresh_bankroll)


def parse_report_time() -> dtime:
    hour, minute = REPORT_TIME.strip().split(":")
    return dtime(int(hour), int(minute), 0)


def get_daily_stats() -> dict:
    return daily_stats


async def run_daily_reset(_: object):
    reset_daily_stats()
    reset_bankroll()
    await refresh_bankroll_async()


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set.")

    start_health_server()

    sync_refresh_bankroll()

    report_time = parse_report_time()
    logger.info(f"Daily report scheduled at {REPORT_TIME} WAT")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    if app.job_queue:
        app.job_queue.run_daily(
            callback=lambda ctx: asyncio.ensure_future(reporter.send_daily_report(dict(daily_stats))),
            time=report_time,
            name="daily_report",
        )

        app.job_queue.run_daily(
            callback=lambda ctx: asyncio.ensure_future(run_daily_reset(ctx)),
            time=dtime(0, 0, 0),
            name="daily_reset",
        )
    else:
        logger.warning(
            "JobQueue is unavailable; skip scheduling daily report/reset. "
            "Install python-telegram-bot[job-queue] to enable these features."
        )

    from bot.listener import handle_message
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("health", make_health_handler(get_daily_stats)))

    logger.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
