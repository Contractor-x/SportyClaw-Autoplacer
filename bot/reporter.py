import logging
import os
from datetime import datetime

from dotenv import load_dotenv

from bot.listener import get_client
from bot.sportybet import SPORTYBET_URL, _login, get_driver

load_dotenv()

logger = logging.getLogger(__name__)

OWNER_USERNAME = os.getenv("OWNER_USERNAME", "").strip().lstrip("@")


def fetch_account_summary() -> dict:
    driver = None
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        driver = get_driver()
        wait = WebDriverWait(driver, 20)
        driver.get(SPORTYBET_URL)
        _login(driver, wait)

        summary = {"account_name": "N/A", "balance": "N/A"}

        name_selectors = [
            "//span[contains(@class,'username')]",
            "//div[contains(@class,'user-name')]",
            "//span[contains(@class,'name')]",
            "//div[contains(@class,'account-name')]",
        ]
        for selector in name_selectors:
            try:
                element = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                summary["account_name"] = (element.text or "").strip() or "N/A"
                break
            except Exception:
                continue

        balance_selectors = [
            "//span[contains(@class,'balance')]",
            "//div[contains(@class,'balance')]",
            "//span[contains(@class,'amount')]",
            "//div[contains(@class,'wallet')]",
            "//*[@data-testid='balance' or contains(@data-testid,'balance')]",
        ]
        for selector in balance_selectors:
            try:
                element = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                summary["balance"] = (element.text or "").strip() or "N/A"
                break
            except Exception:
                continue

        return summary
    except Exception:
        logger.exception("Failed to fetch account summary.")
        return {"account_name": "N/A", "balance": "N/A"}
    finally:
        if driver:
            driver.quit()


def format_report(account: dict, stats: dict) -> str:
    return "\n".join(
        [
            "Daily Report",
            f"{datetime.now().strftime('%A, %d %B %Y')}",
            f"Account name: {account.get('account_name', 'N/A')}",
            f"Balance: {account.get('balance', 'N/A')}",
            f"Bets Placed Today: {stats.get('placed', 0)}",
            f"Won: {stats.get('won', 0)}",
            f"Lost: {stats.get('lost', 0)}",
            f"Ongoing: {stats.get('ongoing', 0)}",
            f"Profit: ₦{stats.get('profit', 0.0):,.2f}",
            f"Loss: ₦{stats.get('loss', 0.0):,.2f}",
        ]
    )


async def send_daily_report() -> None:
    if not OWNER_USERNAME:
        logger.warning("OWNER_USERNAME is not set; skipping daily report.")
        return

    try:
        from bot import main as main_module

        stats = dict(main_module.daily_stats)
        account = fetch_account_summary()
        text = format_report(account, stats)
        client = get_client()
        await client.send_message(OWNER_USERNAME, text)
        logger.info("Daily report sent to @%s", OWNER_USERNAME)
    except Exception:
        logger.exception("Failed to send daily report.")
