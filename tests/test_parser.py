import pytest
from bot.parser import extract_bet_code


@pytest.mark.parametrize(
    "text,expected",
    [
        ("ABC1234", "ABC1234"),
        ("Code: xyz987", "XYZ987"),
        ("Booking: 1A2B3C", "1A2B3C"),
        ("bet code: ABC123", "ABC123"),
    ],
)
def test_extract_codes(text, expected):
    assert extract_bet_code(text) == expected


def test_extract_ignores_words():
    assert extract_bet_code("and") is None


def test_no_text_returns_none():
    assert extract_bet_code("") is None
