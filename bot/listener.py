import asyncio
import logging
import os
from dotenv import load_dotenv

try:
    from telegram import Update
    from telegram.error import TimedOut
    from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
except ModuleNotFoundError:  # pragma: no cover - fallback for lightweight environments
    class Update:  # type: ignore[misc]
        pass

    class ContextTypes:  # type: ignore[misc]
        DEFAULT_TYPE = object

    class _DummyFilters:
        TEXT = None
        COMMAND = None

    filters = _DummyFilters()
    ApplicationBuilder = None  # type: ignore[misc]
    MessageHandler = lambda *args, **kwargs: None  # type: ignore[misc]
    TimedOut = Exception  # type: ignore[misc]

from .parser import extract_bet_code
from sportybet.client import place_bet_with_code
from bankroll import has_available_allocation, reserve_stake, release_stake, get_state

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID")
ALLOWED_USER_IDS = os.getenv("ALLOWED_USER_IDS", "")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def _build_allowed_user_ids() -> set[str]:
    allowed = set()
    if ALLOWED_USER_ID:
        allowed.add(ALLOWED_USER_ID.strip())

    for raw in ALLOWED_USER_IDS.split(","):
        trimmed = raw.strip()
        if trimmed:
            allowed.add(trimmed)

    return allowed


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    sender_id = str(message.from_user.id)
    sender_name = message.from_user.full_name
    text = message.text.strip()

    logger.info(f"Message from {sender_name} ({sender_id}): {text}")

    allowed_ids = _build_allowed_user_ids()
    if allowed_ids and sender_id not in allowed_ids:
        logger.info(f"Ignoring message from unauthorized user {sender_id}")
        return

    code = extract_bet_code(text)
    if not code:
        logger.info("No bet code found in message.")
        return

    if not has_available_allocation():
        logger.info("Daily allocation exhausted.")
        await _reply_with_retry(message, "Daily allocation depleted. Use /health to confirm and try again after the daily reset.")
        return

    stake_amount = reserve_stake()
    if stake_amount is None:
        logger.info("Bankroll not initialized yet.")
        await _reply_with_retry(message, "Allocation is being refreshed—please wait a moment before placing a bet.")
        return

    logger.info(f"Bet code detected: {code} — placing bet...")

    success, result_message = place_bet_with_code(code, stake_amount)

    if success:
        logger.info(f"Bet placed successfully: {result_message}")
        state = get_state()
        await _reply_with_retry(
            message,
            f"✅ Bet placed! Code: {code}\n{result_message}\n"
            f"Allocation remaining: ₦{state['allocation_remaining']:,.2f} "
            f"({state['bets_remaining']}/{state['max_bets_per_day']} bets left)"
        )
    else:
        logger.error(f"Failed to place bet: {result_message}")
        release_stake(stake_amount)
        await _reply_with_retry(message, f"❌ Failed to place bet for code: {code}\nReason: {result_message}")


def start_listener():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set in environment variables.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Listener is running...")
    app.run_polling()


async def _reply_with_retry(message, text: str, attempts: int = 2, delay_seconds: float = 1.0) -> None:
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            await message.reply_text(text)
            return
        except TimedOut as exc:
            last_error = exc
            if attempt < attempts:
                await asyncio.sleep(delay_seconds)
            else:
                raise


if __name__ == "__main__":
    start_listener()
