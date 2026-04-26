import logging
import re

logger = logging.getLogger(__name__)

IGNORE_WORDS = {
    "THE",
    "AND",
    "FOR",
    "WIN",
    "BET",
    "ODD",
    "ODDS",
    "HIGH",
    "LOW",
    "TOP",
    "HOT",
    "TODAY",
    "STAKE",
    "STAKES",
    "MATCH",
    "MATCHES",
    "BOOKING",
    "CODE",
    "SLIP",
    "SPORTY",
    "SPORTYBET",
    "TOTAL",
    "SINGLE",
    "MULTIPLE",
    "SYSTEM",
    "HOME",
    "AWAY",
    "OVER",
    "UNDER",
}

SLIP_KEYWORDS = ("booking", "code", "slip", "stake", "odds", "match", "win", "bet", "sporty", "#")


def _is_valid_code(candidate: str) -> bool:
    code = candidate.strip().upper()
    if len(code) != 6:
        return False
    if code in IGNORE_WORDS:
        return False
    if not re.fullmatch(r"[A-Z0-9]+", code):
        return False
    return bool(re.search(r"[A-Z]", code) and re.search(r"\d", code))


def extract_bet_code(text: str) -> str | None:
    if not text:
        return None

    raw = text.strip()

    # 1) Explicit labels
    explicit_patterns = [
        r"\bBooking(?:\s*Code)?\s*[:\-]?\s*([A-Z0-9]{6})\b",
        r"\bBet\s*Code\s*[:\-]?\s*([A-Z0-9]{6})\b",
        r"\bCode\s*[:\-]?\s*([A-Z0-9]{6})\b",
        r"\bSlip\s*[:\-]?\s*([A-Z0-9]{6})\b",
    ]
    for pattern in explicit_patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if match:
            code = match.group(1).upper()
            if _is_valid_code(code):
                return code

    # 2) Hash prefix
    hash_match = re.search(r"#([A-Z0-9]{6})\b", raw, flags=re.IGNORECASE)
    if hash_match:
        code = hash_match.group(1).upper()
        if _is_valid_code(code):
            return code

    # 3) Standalone line
    for line in reversed(raw.splitlines()):
        candidate = line.strip().upper()
        if not candidate:
            continue
        if re.fullmatch(r"[A-Z0-9]{6}", candidate) and _is_valid_code(candidate):
            return candidate

    # 4) Single-token fallback for short code-only messages.
    tokens = re.findall(r"\b[A-Z0-9]{6}\b", raw.upper())
    if len(tokens) == 1 and _is_valid_code(tokens[0]):
        return tokens[0]

    logger.debug("No bet code found in message.")
    return None


def is_bet_slip(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    hits = sum(1 for keyword in SLIP_KEYWORDS if keyword in lowered)
    return hits >= 2
