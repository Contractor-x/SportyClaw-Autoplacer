import asyncio
import logging
import os
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from bankroll import get_state, initialize_from_amount, reset as reset_bankroll, update_balance_from_raw
from bot.listener import PHONE_NUMBER, get_client, message_betting_bot, register_handlers, start_background_workers
from bot.reporter import fetch_account_summary, send_daily_report

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

MAX_BETS_PER_DAY = int(os.getenv("MAX_BETS_PER_DAY", "30"))
BALANCE_REFRESH_COOLDOWN_SECONDS = int(os.getenv("BALANCE_REFRESH_COOLDOWN_SECONDS", "45"))
BANKROLL_BOOT_RETRY_SECONDS = int(os.getenv("BANKROLL_BOOT_RETRY_SECONDS", "20"))

daily_stats = {
    "placed": 0,
    "won": 0,
    "lost": 0,
    "ongoing": 0,
    "profit": 0.0,
    "loss": 0.0,
}

_balance_lock = asyncio.Lock()
_last_refresh_at: datetime | None = None
_bankroll_ready = asyncio.Event()
_bankroll_bootstrapped = False


async def refresh_bankroll(force: bool = False) -> dict:
    global _last_refresh_at
    async with _balance_lock:
        started_at = datetime.now()
        now = datetime.now()
        if not force and _last_refresh_at and now - _last_refresh_at < timedelta(seconds=BALANCE_REFRESH_COOLDOWN_SECONDS):
            return {"ok": True, "cached": True}

        try:
            account = await asyncio.to_thread(fetch_account_summary)
            if not account.get("ok", True):
                return {"ok": False, "cached": False, "reason": "account-summary-failed"}

            raw_balance = account.get("balance")
            parsed_preview = update_balance_from_raw(raw_balance)
            if parsed_preview <= 0 and str(raw_balance or "").strip().upper() in {"", "N/A", "NA", "NONE"}:
                current = float(get_state().get("current_balance", 0.0))
                if current > 0:
                    logger.warning(
                        "Ignoring invalid balance payload (%r); keeping existing balance %.2f",
                        raw_balance,
                        current,
                    )
                    return {"ok": False, "cached": False, "reason": "invalid-balance-payload"}

            balance = parsed_preview
            initialize_from_amount(balance, max_bets_per_day=MAX_BETS_PER_DAY)
            _last_refresh_at = now
            _bankroll_ready.set()
            elapsed = (datetime.now() - started_at).total_seconds()
            logger.info("Bankroll refresh complete: parsed balance=%.2f in %.1fs", balance, elapsed)
            return {"ok": True, "cached": False, "balance": balance}
        except Exception:
            elapsed = (datetime.now() - started_at).total_seconds()
            logger.exception("Bankroll refresh failed after %.1fs.", elapsed)
            return {"ok": False, "cached": False}


async def ensure_bankroll_initialized(force: bool = False) -> dict:
    global _bankroll_bootstrapped
    if _bankroll_bootstrapped and not force:
        return {"ok": True, "cached": True}
    result = await refresh_bankroll(force=force)
    if result.get("ok"):
        _bankroll_bootstrapped = True
    return result


def is_bankroll_ready() -> bool:
    return _bankroll_ready.is_set()


async def wait_for_bankroll_ready(timeout_seconds: float = 0.0) -> bool:
    if _bankroll_ready.is_set():
        return True
    if timeout_seconds <= 0:
        return False
    try:
        await asyncio.wait_for(_bankroll_ready.wait(), timeout=timeout_seconds)
        return True
    except asyncio.TimeoutError:
        return False


async def run_daily_reset() -> None:
    try:
        reset_bankroll()
        _bankroll_ready.clear()
        await ensure_bankroll_initialized(force=True)
    except Exception:
        logger.exception("Daily reset failed.")


async def _bootstrap_bankroll_until_ready() -> None:
    while True:
        result = await ensure_bankroll_initialized(force=True)
        if result.get("ok"):
            return
        logger.warning(
            "Initial bankroll bootstrap failed, retrying in %s seconds.",
            BANKROLL_BOOT_RETRY_SECONDS,
        )
        await asyncio.sleep(BANKROLL_BOOT_RETRY_SECONDS)


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
    scheduler.add_job(
        run_daily_reset,
        trigger="cron",
        hour=0,
        minute=1,
        id="scheduled-daily-reset",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started: messages at 00:00/12:00, report at 08:00, reset at 00:01")
    return scheduler


async def run() -> None:
    client = get_client()

    scheduler: AsyncIOScheduler | None = None
    try:
        if PHONE_NUMBER:
            await client.start(phone=PHONE_NUMBER)
        else:
            await client.start()
        logger.info("Telethon client started.")

        # Keep startup fast; complete Selenium bankroll initialization in background.
        asyncio.create_task(_bootstrap_bankroll_until_ready())
        start_background_workers()
        register_handlers(client)
        scheduler = _start_scheduler()
        await client.run_until_disconnected()
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
