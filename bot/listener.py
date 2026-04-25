import asyncio
import logging
import os
from typing import Awaitable, Callable

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.custom.message import Message

from bankroll import has_available_allocation, release_stake, reserve_stake
from bot.commands import format_health_text
from bot.parser import extract_bet_code
from bot.sportybet import place_bet_with_code

load_dotenv()

logger = logging.getLogger(__name__)

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "")
SESSION_NAME = os.getenv("TELETHON_SESSION", "session")

TELETHON_CHATS_RAW = os.getenv("TELETHON_CHATS", "").strip()
ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID", "").strip()
ALLOWED_USER_IDS = {item.strip() for item in ALLOWED_USER_ID.split(",") if item.strip()}

BETTING_BOT_USERNAME = os.getenv("BETTING_BOT_USERNAME", "").strip().lstrip("@")
BOT_MESSAGE = os.getenv("BOT_MESSAGE", "give me 5 matches today all high stakes").strip()
HEALTH_REFRESH_BALANCE = str(os.getenv("HEALTH_REFRESH_BALANCE", "0")).strip().lower() in {"1", "true", "yes", "on"}

_client: TelegramClient | None = None
_placement_lock = asyncio.Lock()
_placement_queue: asyncio.Queue[tuple[str, Callable[[str], Awaitable[None]] | None]] = asyncio.Queue()
_worker_task: asyncio.Task | None = None


def _is_truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _parse_chats(raw: str) -> list[str]:
    chats = []
    for part in raw.split(","):
        token = part.strip()
        if token:
            chats.append(token)
    return chats


TELETHON_CHATS = _parse_chats(TELETHON_CHATS_RAW)
TELETHON_REPLY_IN_CHAT = _is_truthy(os.getenv("TELETHON_REPLY_IN_CHAT"))


def get_client() -> TelegramClient:
    global _client
    if _client is None:
        if not API_ID or not API_HASH:
            raise RuntimeError("Missing API_ID or API_HASH.")
        _client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    return _client


def _is_allowed_sender(sender_id: int | None) -> bool:
    if ALLOWED_USER_IDS and sender_id is not None:
        return str(sender_id) in ALLOWED_USER_IDS
    return True


async def _run_placement(code: str) -> tuple[bool, str]:
    try:
        from bot.main import wait_for_bankroll_ready, ensure_bankroll_initialized

        if not await wait_for_bankroll_ready(timeout_seconds=0.1):
            # Trigger lazy init if startup refresh is still in flight.
            await ensure_bankroll_initialized(force=False)
        if not await wait_for_bankroll_ready(timeout_seconds=10):
            return False, "Bankroll is still initializing, retry shortly."
    except Exception:
        logger.exception("Failed checking bankroll readiness before placement.")
        return False, "Could not confirm bankroll status."

    if not has_available_allocation():
        return False, "Daily allocation depleted."

    stake_amount = reserve_stake()
    if stake_amount is None:
        return False, "Allocation unavailable."

    async with _placement_lock:
        try:
            success, details = await asyncio.to_thread(place_bet_with_code, code, stake_amount)
            if success:
                try:
                    from bot import main as main_module

                    main_module.daily_stats["placed"] += 1
                    main_module.daily_stats["ongoing"] += 1
                except Exception:
                    logger.exception("Failed updating daily stats.")
                return True, details
            release_stake(stake_amount)
            return False, details
        except Exception:
            release_stake(stake_amount)
            logger.exception("Unexpected error while placing bet.")
            return False, "Unexpected error during bet placement."


async def _placement_worker() -> None:
    logger.info("Placement worker started.")
    while True:
        code, reply_func = await _placement_queue.get()
        try:
            success, details = await _run_placement(code)
            if reply_func is not None and TELETHON_REPLY_IN_CHAT:
                if success:
                    await reply_func(f"Placed code {code}. {details}")
                else:
                    await reply_func(f"Failed code {code}. {details}")
        except Exception:
            logger.exception("Placement worker failed for code=%s", code)
        finally:
            _placement_queue.task_done()


def start_background_workers() -> None:
    global _worker_task
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(_placement_worker())


async def _handle_health_command(event: events.NewMessage.Event) -> None:
    if HEALTH_REFRESH_BALANCE:
        try:
            from bot.main import refresh_bankroll

            # Keep /health responsive by not forcing a full scrape every time.
            asyncio.create_task(refresh_bankroll(force=False))
        except Exception:
            logger.exception("Balance refresh trigger failed during /health.")

    try:
        from bot import main as main_module

        stats = main_module.daily_stats
        bankroll_ready = main_module.is_bankroll_ready()
    except Exception:
        stats = {"placed": 0, "won": 0, "lost": 0, "ongoing": 0, "profit": 0.0, "loss": 0.0}
        bankroll_ready = False

    await event.respond(format_health_text(stats) + f"\nBankroll initialized: {'yes' if bankroll_ready else 'no'}")


async def _handle_group_message(event: events.NewMessage.Event) -> None:
    message: Message = event.message
    text = (message.raw_text or "").strip()
    if not text:
        return

    sender = await event.get_sender()
    sender_id = getattr(sender, "id", None)
    if not _is_allowed_sender(sender_id):
        return

    code = extract_bet_code(text)
    if not code:
        return

    logger.info("Group code extracted: %s", code)
    reply_func = event.reply if TELETHON_REPLY_IN_CHAT else None
    await _placement_queue.put((code, reply_func))


async def _handle_betting_bot_reply(event: events.NewMessage.Event) -> None:
    message: Message = event.message
    text = (message.raw_text or "").strip()
    if not text:
        return

    code = extract_bet_code(text)
    if not code:
        return

    logger.info("Bot reply code extracted: %s", code)
    reply_func = event.reply if TELETHON_REPLY_IN_CHAT else None
    await _placement_queue.put((code, reply_func))


def register_handlers(client: TelegramClient) -> None:
    client.add_event_handler(_handle_health_command, events.NewMessage(pattern=r"^/health$"))

    if TELETHON_CHATS:
        client.add_event_handler(_handle_group_message, events.NewMessage(chats=TELETHON_CHATS))
        logger.info("Registered group handler for chats: %s", ", ".join(TELETHON_CHATS))
    else:
        logger.warning("TELETHON_CHATS is not set. Group monitoring is disabled.")

    if BETTING_BOT_USERNAME:
        client.add_event_handler(_handle_betting_bot_reply, events.NewMessage(from_users=BETTING_BOT_USERNAME))
        logger.info("Registered betting bot reply handler for @%s", BETTING_BOT_USERNAME)
    else:
        logger.warning("BETTING_BOT_USERNAME is not set. Betting bot reply monitoring is disabled.")


async def message_betting_bot() -> None:
    if not BETTING_BOT_USERNAME:
        logger.warning("Skipping scheduled message: BETTING_BOT_USERNAME not configured.")
        return
    if not BOT_MESSAGE:
        logger.warning("Skipping scheduled message: BOT_MESSAGE is empty.")
        return
    client = get_client()
    await client.send_message(BETTING_BOT_USERNAME, BOT_MESSAGE)
    logger.info("Scheduled message sent to @%s", BETTING_BOT_USERNAME)
