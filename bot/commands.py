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
            f"Available quarters: {bankroll_state['chunks_available']}/"
            f"{bankroll_state['total_chunks']} (₦{bankroll_state['chunk_value']:,.2f} each)"
        )
        logger.info("Health command replied with current stats.")
        await update.message.reply_text(text)

    return health
