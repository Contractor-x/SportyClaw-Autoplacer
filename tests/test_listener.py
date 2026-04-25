import pytest

pytest.importorskip("telethon")

from bot import listener, main as main_module


class _FakeHealthEvent:
    def __init__(self):
        self.responses = []
        self.replies = []

    async def respond(self, text: str):
        self.responses.append(text)

    async def reply(self, text: str):
        self.replies.append(text)


@pytest.mark.asyncio
async def test_health_uses_respond_not_reply(monkeypatch):
    event = _FakeHealthEvent()
    monkeypatch.setattr(listener, "HEALTH_REFRESH_BALANCE", False)
    monkeypatch.setattr(main_module, "is_bankroll_ready", lambda: True)
    main_module.daily_stats.update({"placed": 1, "won": 0, "lost": 0, "ongoing": 1, "profit": 0.0, "loss": 0.0})

    await listener._handle_health_command(event)

    assert len(event.responses) == 1
    assert not event.replies
    assert "Bankroll initialized: yes" in event.responses[0]


def test_allowed_sender_single_or_many_ids(monkeypatch):
    monkeypatch.setattr(listener, "ALLOWED_USER_IDS", {"42", "99"})
    assert listener._is_allowed_sender(42)
    assert listener._is_allowed_sender(99)
    assert not listener._is_allowed_sender(100)


@pytest.mark.asyncio
async def test_run_placement_success_updates_stats(monkeypatch):
    monkeypatch.setattr(main_module, "wait_for_bankroll_ready", lambda timeout_seconds=0.0: _true())
    monkeypatch.setattr(main_module, "ensure_bankroll_initialized", lambda force=False: _ok())
    monkeypatch.setattr(listener, "has_available_allocation", lambda: True)
    monkeypatch.setattr(listener, "reserve_stake", lambda: 100.0)
    monkeypatch.setattr(listener, "place_bet_with_code", lambda code, stake: (True, "ok"))

    main_module.daily_stats.update({"placed": 0, "won": 0, "lost": 0, "ongoing": 0, "profit": 0.0, "loss": 0.0})
    success, _ = await listener._run_placement("ABC123")

    assert success is True
    assert main_module.daily_stats["placed"] == 1
    assert main_module.daily_stats["ongoing"] == 1


@pytest.mark.asyncio
async def test_run_placement_releases_stake_on_failure(monkeypatch):
    released = {"amount": 0.0}

    monkeypatch.setattr(main_module, "wait_for_bankroll_ready", lambda timeout_seconds=0.0: _true())
    monkeypatch.setattr(main_module, "ensure_bankroll_initialized", lambda force=False: _ok())
    monkeypatch.setattr(listener, "has_available_allocation", lambda: True)
    monkeypatch.setattr(listener, "reserve_stake", lambda: 50.0)
    monkeypatch.setattr(listener, "release_stake", lambda amount: released.__setitem__("amount", amount))
    monkeypatch.setattr(listener, "place_bet_with_code", lambda code, stake: (False, "failed"))

    success, _ = await listener._run_placement("ABC123")

    assert success is False
    assert released["amount"] == 50.0


async def _true():
    return True


async def _ok():
    return {"ok": True}
