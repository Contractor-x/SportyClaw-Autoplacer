import asyncio
import logging
import os
from typing import Callable
from telegram.error import TimedOut
from telegram import Update
from telegram.ext import ContextTypes

import reporter
from bankroll import get_state, update_balance_from_raw

logger = logging.getLogger(__name__)


def make_health_handler(get_daily_stats: Callable[[], dict]):
    async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if os.getenv("HEALTH_REFRESH_BALANCE", "1") == "1":
            async def _refresh_balance():
                try:
                    account = await asyncio.to_thread(reporter.fetch_account_summary)
                    update_balance_from_raw(account.get("balance"))
                except Exception:
                    logger.exception("Balance refresh failed during /health")

            context.application.create_task(_refresh_balance())

        stats = get_daily_stats()
        bankroll_state = get_state()
        text = (
            "Bot status: ✅\n"
            f"Bets today: placed={stats['placed']} won={stats['won']} "
            f"lost={stats['lost']} ongoing={stats['ongoing']}\n"
            f"Profit: ₦{stats['profit']:,.2f} / Loss: ₦{stats['loss']:,.2f}\n"
            f"Account balance: ₦{bankroll_state['current_balance']:,.2f}\n"
            f"Starting balance: ₦{bankroll_state['starting_balance']:,.2f}\n"
            f"Daily allocation: ₦{bankroll_state['allocation_remaining']:,.2f} remaining / "
            f"₦{bankroll_state['allocation_total']:,.2f} total\n"
            f"Bets left today: {bankroll_state['bets_remaining']}/"
            f"{bankroll_state['max_bets_per_day']}\n"
            f"Reserve balance: ₦{bankroll_state['reserve']:,.2f}"
        )
        logger.info("Health command replied with current stats.")
        await _reply_with_retry(update, text)

    return health


async def _reply_with_retry(update: Update, text: str, attempts: int = 3, delay_seconds: float = 1.0) -> None:
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            await update.message.reply_text(text)
            return
        except TimedOut as exc:
            last_error = exc
            if attempt < attempts:
                await asyncio.sleep(delay_seconds * attempt)
            else:
                raise
