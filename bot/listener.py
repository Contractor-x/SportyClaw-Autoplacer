import logging
import os
from typing import Awaitable, Callable

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.custom.message import Message

from bot.parser import extract_bet_code
from bot.sportybet import place_bet_with_code

load_dotenv()

logger = logging.getLogger(__name__)

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "")
SESSION_NAME = os.getenv("TELETHON_SESSION", "session")

GROUP_USERNAME = os.getenv("GROUP_USERNAME", "").strip()

BETTING_BOT_USERNAME = os.getenv("BETTING_BOT_USERNAME", "").strip().lstrip("@")
BOT_MESSAGE = os.getenv("BOT_MESSAGE", "Analyze football/Basketball matches using team form, head-to-head history, injuries and standings. Pick the 5 highest confidence matches and return them as 5 separate SportyBet booking codes, one per match, labelled Slip 1 through Slip 5.").strip()

_client: TelegramClient | None = None


def get_client() -> TelegramClient:
    global _client
    if _client is None:
        if not API_ID or not API_HASH:
            raise RuntimeError("Missing API_ID or API_HASH.")
        _client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    return _client




def _run_placement(code: str) -> None:
    try:
        success, details = place_bet_with_code(code)
        if success:
            logger.info("Bet placed from Telethon flow: %s", details)
        else:
            logger.warning("Bet placement failed from Telethon flow: %s", details)
    except Exception:
        logger.exception("Unexpected error while placing bet from Telethon flow.")


async def _handle_group_message(event: events.NewMessage.Event) -> None:
    message: Message = event.message
    text = (message.raw_text or "").strip()
    if not text:
        return

    code = extract_bet_code(text)
    if not code:
        return

    logger.info("Group listener extracted code: %s", code)
    _run_placement(code)


async def _handle_betting_bot_reply(event: events.NewMessage.Event) -> None:
    message: Message = event.message
    text = (message.raw_text or "").strip()
    if not text:
        return

    code = extract_bet_code(text)
    if not code:
        logger.info("No booking code found in betting bot reply.")
        return

    logger.info("Betting bot reply extracted code: %s", code)
    _run_placement(code)


def register_handlers(client: TelegramClient) -> None:
    if GROUP_USERNAME:
        client.add_event_handler(_handle_group_message, events.NewMessage(chats=GROUP_USERNAME))
        logger.info("Registered group handler for %s", GROUP_USERNAME)
    else:
        logger.warning("GROUP_USERNAME is not set. Group monitoring is disabled.")

    if BETTING_BOT_USERNAME:
        client.add_event_handler(
            _handle_betting_bot_reply,
            events.NewMessage(from_users=BETTING_BOT_USERNAME),
        )
        logger.info("Registered betting bot reply handler for @%s", BETTING_BOT_USERNAME)
    else:
        logger.warning("BETTING_BOT_USERNAME is not set. Betting bot reply monitoring is disabled.")


async def message_betting_bot() -> None:
    if not BETTING_BOT_USERNAME:
        logger.warning("Skipping scheduled message: BETTING_BOT_USERNAME is not configured.")
        return
    if not BOT_MESSAGE:
        logger.warning("Skipping scheduled message: BOT_MESSAGE is empty.")
        return

    client = get_client()
    try:
        await client.send_message(BETTING_BOT_USERNAME, BOT_MESSAGE)
        logger.info("Scheduled message sent to @%s", BETTING_BOT_USERNAME)
    except Exception:
        logger.exception("Failed to send scheduled message to @%s", BETTING_BOT_USERNAME)
