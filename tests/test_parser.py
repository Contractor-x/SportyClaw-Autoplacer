import pytest
from bot.parser import extract_bet_code


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Code: xyz987", "XYZ987"),
        ("Booking: 1A2B3C", "1A2B3C"),
        ("bet code: ABC123", "ABC123"),
        (
            "Here’s what the data supports:\n\nBest picks for today\n\nX2MN4T",
            "X2MN4T",
        ),
    ],
)
def test_extract_codes(text, expected):
    assert extract_bet_code(text) == expected


def test_extract_ignores_words():
    assert extract_bet_code("and") is None
    assert extract_bet_code("PROCESSING") is None
    assert extract_bet_code("FOLLOW") is None
    assert extract_bet_code("ABC1234") is None


def test_no_text_returns_none():
    assert extract_bet_code("") is None
