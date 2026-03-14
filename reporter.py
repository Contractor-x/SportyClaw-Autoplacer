import os
import logging
from datetime import datetime
from telegram import Bot
from sportybet.client import get_driver, _login, SPORTYBET_URL

logger = logging.getLogger(__name__)

OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID")  # Your own Telegram chat ID
BOT_TOKEN = os.getenv("BOT_TOKEN")


def fetch_account_summary() -> dict:
    """Logs into SportyBet and scrapes account info."""
    driver = None
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time

        driver = get_driver()
        wait = WebDriverWait(driver, 15)

        driver.get(SPORTYBET_URL)
        _login(driver, wait)
        time.sleep(3)

        summary = {
            "account_name": "N/A",
            "balance": "N/A",
        }

        # Account name
        name_selectors = [
            "//span[contains(@class,'username')]",
            "//div[contains(@class,'user-name')]",
            "//span[contains(@class,'name')]",
            "//div[contains(@class,'account-name')]",
        ]
        for sel in name_selectors:
            try:
                el = wait.until(EC.presence_of_element_located((By.XPATH, sel)))
                summary["account_name"] = el.text.strip()
                break
            except Exception:
                continue

        # Balance
        balance_selectors = [
            "//span[contains(@class,'balance')]",
            "//div[contains(@class,'balance')]",
            "//span[contains(@class,'amount')]",
            "//div[contains(@class,'wallet')]",
        ]
        for sel in balance_selectors:
            try:
                el = wait.until(EC.presence_of_element_located((By.XPATH, sel)))
                summary["balance"] = el.text.strip()
                break
            except Exception:
                continue

        return summary

    except Exception as e:
        logger.exception("Failed to fetch account summary.")
        return {"account_name": "N/A", "balance": "N/A"}
    finally:
        if driver:
            driver.quit()


def format_report(account: dict, stats: dict) -> str:
    today = datetime.now().strftime("%A, %d %B %Y")

    lines = [
        f"📊 *Daily Bet Report*",
        f"📅 {today}",
        f"",
        f"👤 *Account:* {account['account_name']}",
        f"💰 *Balance:* {account['balance']}",
        f"",
        f"🎯 *Bets Placed Today:* {stats['placed']}",
        f"✅ *Won:* {stats['won']}",
        f"❌ *Lost:* {stats['lost']}",
        f"⏳ *Ongoing:* {stats['ongoing']}",
        f"",
        f"📈 *Profit:* ₦{stats['profit']:,.2f}",
        f"📉 *Loss:* ₦{stats['loss']:,.2f}",
        f"",
        f"🤖 _SportyBot auto-report_",
    ]
    return "\n".join(lines)


async def send_daily_report(stats: dict):
    if not OWNER_CHAT_ID:
        logger.warning("OWNER_CHAT_ID not set — skipping daily report.")
        return

    try:
        account = fetch_account_summary()
        message = format_report(account, stats)

        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=message,
            parse_mode="Markdown"
        )
        logger.info("Daily report sent successfully.")

    except Exception as e:
        logger.exception(f"Failed to send daily report: {e}")
