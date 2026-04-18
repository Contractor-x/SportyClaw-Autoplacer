import asyncio
import logging
import os
import threading

from .listener import process_incoming_text

logger = logging.getLogger(__name__)


def _as_bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _parse_chats(raw: str) -> list[str]:
    chats = []
    for part in raw.split(","):
        token = part.strip()
        if token:
            chats.append(token)
    return chats


async def start_telethon_listener() -> None:
    try:
        from telethon import TelegramClient, events
    except ModuleNotFoundError as exc:
        raise RuntimeError("Telethon is not installed. Add telethon to requirements.") from exc

    api_id_raw = os.getenv("TELETHON_API_ID", "").strip()
    api_hash = os.getenv("TELETHON_API_HASH", "").strip()
    phone = os.getenv("TELETHON_PHONE", "").strip()
    session = os.getenv("TELETHON_SESSION", "sportyclaw_telethon")
    chats = _parse_chats(os.getenv("TELETHON_CHATS", ""))
    reply_in_chat = _as_bool(os.getenv("TELETHON_REPLY_IN_CHAT"))

    if not api_id_raw or not api_hash:
        raise RuntimeError("TELETHON_API_ID and TELETHON_API_HASH must be set when TELETHON_ENABLED=1.")

    if not chats:
        raise RuntimeError("TELETHON_CHATS must be set when TELETHON_ENABLED=1 (comma-separated usernames/IDs).")

    api_id = int(api_id_raw)
    client = TelegramClient(session, api_id, api_hash)

    @client.on(events.NewMessage(chats=chats))
    async def _telethon_handler(event):
        text = (event.raw_text or "").strip()
        sender_id = str(event.sender_id or "")
        sender_name = "TelethonUser"
        if event.sender:
            sender_name = getattr(event.sender, "first_name", None) or getattr(event.sender, "username", None) or sender_name

        reply_func = event.reply if reply_in_chat else None
        await process_incoming_text(sender_id, sender_name, text, reply_func)

    logger.info("Starting Telethon listener for chats: %s", ", ".join(chats))
    if phone:
        await client.start(phone=phone)
    else:
        await client.start()
    await client.run_until_disconnected()


def run_telethon_listener_in_thread() -> threading.Thread:
    def _runner():
        asyncio.run(start_telethon_listener())

    thread = threading.Thread(target=_runner, daemon=True, name="telethon-listener")
    thread.start()
    return thread
