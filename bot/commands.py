import logging
from typing import Callable
from telegram import Update
from telegram.ext import ContextTypes

from bankroll import get_state

logger = logging.getLogger(__name__)


def make_health_handler(get_daily_stats: Callable[[], dict]):
    async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
        stats = get_daily_stats()
        bankroll_state = get_state()
        text = (
            "Bot status: ✅\n"
            f"Bets today: placed={stats['placed']} won={stats['won']} "
            f"lost={stats['lost']} ongoing={stats['ongoing']}\n"
            f"Profit: ₦{stats['profit']:,.2f} / Loss: ₦{stats['loss']:,.2f}\n"
            f"Starting balance: ₦{bankroll_state['starting_balance']:,.2f}\n"
            f"Daily allocation: ₦{bankroll_state['allocation_remaining']:,.2f} remaining / "
            f"₦{bankroll_state['allocation_total']:,.2f} total\n"
            f"Bets left today: {bankroll_state['bets_remaining']}/"
            f"{bankroll_state['max_bets_per_day']}\n"
            f"Reserve balance: ₦{bankroll_state['reserve']:,.2f}"
        )
        logger.info("Health command replied with current stats.")
        await update.message.reply_text(text)

    return health
