import logging
import os
from dotenv import load_dotenv

try:
    from telegram import Update
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

from .parser import extract_bet_code
from sportybet.client import place_bet_with_code

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    sender_id = str(message.from_user.id)
    sender_name = message.from_user.full_name
    text = message.text.strip()

    logger.info(f"Message from {sender_name} ({sender_id}): {text}")

    if ALLOWED_USER_ID and sender_id != ALLOWED_USER_ID:
        logger.info(f"Ignoring message from unauthorized user {sender_id}")
        return

    code = extract_bet_code(text)
    if not code:
        logger.info("No bet code found in message.")
        return

    logger.info(f"Bet code detected: {code} — placing bet...")

    success, result_message = place_bet_with_code(code)

    if success:
        logger.info(f"Bet placed successfully: {result_message}")
        await message.reply_text(f"✅ Bet placed! Code: {code}\n{result_message}")
    else:
        logger.error(f"Failed to place bet: {result_message}")
        await message.reply_text(f"❌ Failed to place bet for code: {code}\nReason: {result_message}")


def start_listener():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set in environment variables.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Listener is running...")
    app.run_polling()


if __name__ == "__main__":
    start_listener()
