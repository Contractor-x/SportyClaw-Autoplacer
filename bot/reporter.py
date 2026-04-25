import logging
import os
import re
from datetime import datetime

from dotenv import load_dotenv

from bot.listener import get_client
from bot.sportybet import SPORTYBET_URL, _login, get_driver

load_dotenv()

logger = logging.getLogger(__name__)

OWNER_USERNAME = os.getenv("OWNER_USERNAME", "").strip().lstrip("@")


def _extract_balance_value(text: str) -> str | None:
    if not text:
        return None
    patterns = [
        r"(?i)(?:balance|wallet|available)\s*[:\-]?\s*(?:₦|NGN)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
        r"(?i)(?:₦|NGN)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*(?:balance|wallet|available)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return f"₦{match.group(1)}"
    return None


def fetch_account_summary() -> dict:
    driver = None
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException
        from selenium.webdriver.support.ui import WebDriverWait

        driver = get_driver()
        wait = WebDriverWait(driver, 20)
        short_wait = WebDriverWait(driver, 4)
        balance_wait = WebDriverWait(driver, 12)
        try:
            driver.get(SPORTYBET_URL)
        except TimeoutException:
            # SportyBet can partially render before the full page load completes.
            logger.warning("Timed out loading SportyBet homepage; continuing with partial render.")
            driver.execute_script("window.stop();")
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
                element = short_wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                summary["account_name"] = (element.text or "").strip() or "N/A"
                break
            except Exception:
                continue

        balance_selectors = [
            "//span[contains(@class,'balance')]",
            "//div[contains(@class,'balance')]",
            "//div[contains(@class,'wallet')]",
            "//*[@data-testid='balance' or contains(@data-testid,'balance')]",
            "//header//*[contains(.,'NGN') or contains(.,'₦')]",
            "//*[contains(@class,'account') and (contains(.,'NGN') or contains(.,'₦'))]",
        ]
        for selector in balance_selectors:
            try:
                element = balance_wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                candidate_text = (element.text or "").strip()
                parsed_candidate = _extract_balance_value(candidate_text)
                if parsed_candidate:
                    summary["balance"] = parsed_candidate
                    break
                plain_match = re.search(r"(?:₦|NGN)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", candidate_text, flags=re.IGNORECASE)
                if plain_match:
                    summary["balance"] = f"₦{plain_match.group(1)}"
                    break
            except Exception:
                continue

        if summary["balance"] == "N/A":
            body_text = (driver.find_element(By.TAG_NAME, "body").text or "").strip()
            parsed_candidate = _extract_balance_value(body_text)
            if parsed_candidate:
                summary["balance"] = parsed_candidate

        summary["ok"] = summary["balance"] != "N/A" and bool(re.search(r"\d", summary["balance"]))
        return summary
    except Exception:
        logger.exception("Failed to fetch account summary.")
        return {"account_name": "N/A", "balance": "N/A", "ok": False}
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
