import logging
import os
import time

logger = logging.getLogger(__name__)

SPORTYBET_URL = "https://www.sportybet.com/ng/"
_CACHED_DRIVER_PATH: str | None = None


def _get_credentials() -> tuple[str | None, str | None]:
    return os.getenv("SPORTYBET_PHONE"), os.getenv("SPORTYBET_PASSWORD")


def get_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options

    options = Options()
    options.page_load_strategy = "eager"
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    chrome_bin = os.getenv("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    driver_path = _get_driver_path()
    driver_path = _resolve_driver_executable(driver_path)
    _ensure_executable(driver_path)
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver


def _get_driver_path() -> str:
    global _CACHED_DRIVER_PATH
    if _CACHED_DRIVER_PATH:
        return _CACHED_DRIVER_PATH
    env_path = os.getenv("CHROMEDRIVER_PATH")
    if env_path:
        _CACHED_DRIVER_PATH = env_path
        return env_path
    from webdriver_manager.chrome import ChromeDriverManager

    _CACHED_DRIVER_PATH = ChromeDriverManager().install()
    return _CACHED_DRIVER_PATH


def place_bet_with_code(code: str, stake_amount: float | None = None) -> tuple[bool, str]:
    phone, password = _get_credentials()
    if not phone or not password:
        return False, "SportyBet credentials are not set in environment variables."

    driver = None
    try:
        driver = get_driver()
        from selenium.webdriver.support.ui import WebDriverWait

        wait = WebDriverWait(driver, 15)

        logger.info("Navigating to SportyBet...")
        driver.get(SPORTYBET_URL)

        logger.info("Logging in...")
        _login(driver, wait)

        logger.info(f"Entering booking code: {code}")
        result = _enter_booking_code(driver, wait, code, stake_amount)

        return result

    except Exception as e:
        logger.exception("Unexpected error during bet placement.")
        return False, str(e)

    finally:
        if driver:
            driver.quit()


def _login(driver, wait):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC

    try:
        phone, password = _get_credentials()
        if not phone or not password:
            raise Exception("SportyBet credentials are missing. Set SPORTYBET_PHONE and SPORTYBET_PASSWORD.")

        login_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(text(),'Login')] | //a[contains(text(),'Login')]")
        ))
        login_btn.click()

        phone_input = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[@type='tel' or @name='phone' or contains(@placeholder,'Phone')]")
        ))
        phone_input.clear()
        phone_input.send_keys(phone)

        password_input = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[@type='password']")
        ))
        password_input.clear()
        password_input.send_keys(password)

        submit_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[@type='submit' or contains(text(),'Login')]")
        ))
        submit_btn.click()

        time.sleep(3)
        logger.info("Login submitted.")

    except Exception as e:
        raise Exception(f"Login failed: {e}")


def _enter_booking_code(driver, wait, code: str, stake_amount: float | None) -> tuple[bool, str]:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC

    try:
        booking_selectors = [
            "//a[contains(text(),'Booking Code')]",
            "//button[contains(text(),'Booking Code')]",
            "//a[contains(text(),'Bet Code')]",
            "//span[contains(text(),'Booking Code')]",
        ]

        clicked = False
        for selector in booking_selectors:
            try:
                btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                btn.click()
                clicked = True
                logger.info(f"Clicked booking code via: {selector}")
                break
            except Exception:
                continue

        if not clicked:
            driver.get(f"{SPORTYBET_URL}#booking-code")

        time.sleep(2)

        _enable_one_cut(driver, wait)
        if stake_amount is not None and stake_amount > 0:
            _set_stake_amount(driver, wait, stake_amount)

        code_input_selectors = [
            "//input[contains(@placeholder,'code') or contains(@placeholder,'Code')]",
            "//input[contains(@placeholder,'booking') or contains(@placeholder,'Booking')]",
            "//input[contains(@name,'code') or contains(@name,'booking')]",
        ]

        filled = False
        for selector in code_input_selectors:
            try:
                inp = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                inp.clear()
                inp.send_keys(code)
                filled = True
                logger.info(f"Filled code using: {selector}")
                break
            except Exception:
                continue

        if not filled:
            return False, "Could not find the booking code input. SportyBet UI may have changed."

        confirm_selectors = [
            "//button[contains(text(),'Load')]",
            "//button[contains(text(),'Confirm')]",
            "//button[contains(text(),'Place Bet')]",
            "//button[contains(text(),'Submit')]",
            "//button[@type='submit']",
        ]

        confirmed = False
        for selector in confirm_selectors:
            try:
                btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                btn.click()
                confirmed = True
                logger.info(f"Clicked confirm via: {selector}")
                break
            except Exception:
                continue

        if not confirmed:
            return False, "Could not click the confirm/place bet button."

        time.sleep(3)

        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if any(word in page_text for word in ["success", "placed", "confirmed", "accepted"]):
            return True, "Bet placed and confirmed on SportyBet."
        elif any(word in page_text for word in ["invalid", "expired", "error", "failed", "not found"]):
            return False, "SportyBet rejected the code — it may be invalid or expired."
        else:
            return True, "Bet submitted. Please verify on SportyBet."

    except Exception as e:
        raise Exception(f"Booking code entry failed: {e}")


def _enable_one_cut(driver, wait) -> bool:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC

    selectors = [
        "//button[contains(translate(normalize-space(.), 'ONE CUT', 'one cut'), 'one cut')]",
        "//label[contains(translate(normalize-space(.), 'ONE CUT', 'one cut'), 'one cut')]",
        "//span[contains(translate(normalize-space(.), 'ONE CUT', 'one cut'), 'one cut')]/ancestor::button[1]",
        "//div[contains(translate(normalize-space(.), 'ONE CUT', 'one cut'), 'one cut')]//input",
        "//div[contains(@class, 'one-cut') or contains(@class, 'one_cut') or contains(@data-testid, 'oneCut')]",
    ]

    for selector in selectors:
        try:
            toggle = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", toggle)
            toggle.click()
            logger.info("One Cut option activated via %s", selector)
            time.sleep(0.5)
            return True
        except Exception:
            continue

    logger.info("One Cut option not present or already active; continuing without toggling.")
    return False


def _set_stake_amount(driver, wait, amount: float) -> bool:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support import expected_conditions as EC

    formatted = f"{amount:.2f}".rstrip("0").rstrip(".")
    selectors = [
        "//input[contains(translate(@placeholder, 'STAKE', 'stake'), 'stake')]",
        "//label[contains(translate(normalize-space(.), 'STAKE', 'stake'), 'stake')]/following::input[1]",
        "//input[@name='stake']",
        "//input[contains(@class, 'stake')]",
        "//input[contains(@id, 'stake')]",
        "//input[@aria-label='Stake']",
        "//input[@type='number']",
    ]

    for selector in selectors:
        try:
            stake_input = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", stake_input)
            stake_input.click()
            stake_input.send_keys(Keys.CONTROL, "a")
            stake_input.send_keys(formatted)
            stake_input.send_keys(Keys.TAB)
            logger.info("Stake set to %s via %s", formatted, selector)
            time.sleep(0.5)
            return True
        except Exception:
            continue

    logger.info("Stake input not located; leaving default stake amount.")
    return False


def _resolve_driver_executable(path: str) -> str:
    basename = os.path.basename(path).lower()
    if basename.startswith("chromedriver"):
        return path

    directory = os.path.dirname(path)
    try:
        candidates = sorted(os.listdir(directory))
    except OSError:
        raise RuntimeError(f"Unable to inspect driver directory: {directory}")

    for candidate in candidates:
        candidate_lower = candidate.lower()
        if not candidate_lower.startswith("chromedriver"):
            continue
        resolved = os.path.join(directory, candidate)
        if os.path.isfile(resolved):
            return resolved

    raise RuntimeError(f"Could not locate the ChromeDriver binary in {directory} (wrote {path})")


def _ensure_executable(path: str) -> None:
    try:
        os.chmod(path, 0o755)
    except OSError:
        logger.exception("Failed to set executable permissions on %s", path)
