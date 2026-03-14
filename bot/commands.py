import logging
from typing import Callable
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def make_health_handler(get_daily_stats: Callable[[], dict]):
    async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
        stats = get_daily_stats()
        text = (
            "Bot status: ✅\n"
            f"Bets today: placed={stats['placed']} won={stats['won']} "
            f"lost={stats['lost']} ongoing={stats['ongoing']}\n"
            f"Profit: ₦{stats['profit']:,.2f} / Loss: ₦{stats['loss']:,.2f}"
        )
        logger.info("Health command replied with current stats.")
        await update.message.reply_text(text)

    return health
