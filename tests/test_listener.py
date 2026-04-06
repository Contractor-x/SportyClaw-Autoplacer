import pytest

from bot import listener
from bot.mock_handler import create_mock_update


@pytest.mark.asyncio
async def test_handle_message_places_bet(monkeypatch):
    monkeypatch.setattr(listener, "ALLOWED_USER_ID", "42")
    monkeypatch.setattr(listener, "has_available_allocation", lambda: True)
    monkeypatch.setattr(listener, "reserve_stake", lambda: 100)
    monkeypatch.setattr(
        listener,
        "get_state",
        lambda: {"allocation_remaining": 300, "bets_remaining": 3, "max_bets_per_day": 30},
    )
    update = create_mock_update("Booking: ABC123", user_id=42)
    monkeypatch.setattr(listener, "place_bet_with_code", lambda code, stake=None: (True, "ok"))

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


@pytest.mark.asyncio
async def test_handle_message_accepts_additional_authorized_user(monkeypatch):
    monkeypatch.setattr(listener, "ALLOWED_USER_ID", "")
    monkeypatch.setattr(listener, "ALLOWED_USER_IDS", "42, 99")
    monkeypatch.setattr(listener, "has_available_allocation", lambda: True)
    monkeypatch.setattr(listener, "reserve_stake", lambda: 100)
    monkeypatch.setattr(
        listener,
        "get_state",
        lambda: {"allocation_remaining": 300, "bets_remaining": 3, "max_bets_per_day": 30},
    )
    update = create_mock_update("Booking: ABC123", user_id=42)
    monkeypatch.setattr(listener, "place_bet_with_code", lambda code, stake=None: (True, "ok"))

    await listener.handle_message(update, None)

    assert update.message.reply_texts
    assert "✅" in update.message.reply_texts[0]
