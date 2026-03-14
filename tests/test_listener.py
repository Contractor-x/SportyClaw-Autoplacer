import pytest

from bot import listener
from bot.mock_handler import create_mock_update


@pytest.mark.asyncio
async def test_handle_message_places_bet(monkeypatch):
    monkeypatch.setattr(listener, "ALLOWED_USER_ID", "42")
    update = create_mock_update("Booking: ABC123", user_id=42)
    monkeypatch.setattr(listener, "place_bet_with_code", lambda code: (True, "ok"))

    await listener.handle_message(update, None)

    assert update.message.reply_texts
    assert "✅" in update.message.reply_texts[0]


@pytest.mark.asyncio
async def test_handle_message_ignores_unauthorized(monkeypatch):
    monkeypatch.setattr(listener, "ALLOWED_USER_ID", "100")
    update = create_mock_update("Booking: ABC123", user_id=42)
    replies_before = len(update.message.reply_texts)

    await listener.handle_message(update, None)

    assert len(update.message.reply_texts) == replies_before
