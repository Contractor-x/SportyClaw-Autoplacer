import re
import logging

logger = logging.getLogger(__name__)

# SportyBet booking codes are typically 7 uppercase alphanumeric characters
# but can vary. Adjust patterns below if your friend formats them differently.

PATTERNS = [
    # Plain code alone on a line or in message e.g. "ABC1234"
    r'(?<![A-Z0-9])([A-Z0-9]{5,12})(?![A-Z0-9])',

    # "Code: ABC1234" or "code: ABC1234"
    r'[Cc]ode[:\s]+([A-Z0-9]{5,12})',

    # "Booking: ABC1234" or "Booking Code: ABC1234"
    r'[Bb]ook(?:ing)?(?:\s+[Cc]ode)?[:\s]+([A-Z0-9]{5,12})',

    # "Bet code: ABC1234"
    r'[Bb]et\s+[Cc]ode[:\s]+([A-Z0-9]{5,12})',
]

# Words to ignore so common English words don't get picked up as codes
IGNORE_WORDS = {
    "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL",
    "CAN", "HER", "WAS", "ONE", "OUR", "OUT", "DAY", "GET",
    "HAS", "HIM", "HIS", "HOW", "ITS", "NOW", "OLD", "SEE",
    "TWO", "WHO", "BOY", "DID", "ITS", "LET", "PUT", "SAY",
    "TOO", "USE", "WIN", "BET", "ODD", "YES", "MAN",
}


def extract_bet_code(text: str) -> str | None:
    """
    Extracts a SportyBet booking code from a message string.
    Returns the code string if found, or None if no code is detected.
    """
    if not text:
        return None

    # Normalize: strip extra whitespace
    text = text.strip()

    for pattern in PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            code = match.upper()
            if code in IGNORE_WORDS:
                logger.debug(f"Skipping common word: {code}")
                continue
            if len(code) < 5:
                continue
            logger.info(f"Extracted bet code: {code}")
            return code

    logger.debug("No bet code found in message.")
    return None


def is_likely_bet_message(text: str) -> bool:
    """
    Optional helper — returns True if the message looks like it's
    about a bet, even before a code is extracted.
    Useful for logging or filtering.
    """
    keywords = ["bet", "code", "booking", "sporty", "odds", "stake", "win", "game"]
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)