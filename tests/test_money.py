import pytest

from carecircle.money import MoneyError, format_rupees, parse_rupees


@pytest.mark.parametrize(
    "text, paise",
    [
        ("2400", 240000),
        ("2,400", 240000),
        ("₹2,400", 240000),
        ("Rs 2400", 240000),
        ("rs.2400", 240000),
        ("INR 1,20,000", 12000000),
        ("99.5", 9950),
        ("0.01", 1),
    ],
)
def test_parse(text, paise):
    assert parse_rupees(text) == paise


@pytest.mark.parametrize("text", ["", "abc", "0", "-5", "12.345", "2,40,0x"])
def test_parse_rejects(text):
    with pytest.raises(MoneyError):
        parse_rupees(text)


@pytest.mark.parametrize(
    "paise, text",
    [
        (240000, "₹2,400"),
        (12000000, "₹1,20,000"),
        (1234567850, "₹1,23,45,678.50"),
        (9950, "₹99.50"),
        (-80000, "-₹800"),
        (0, "₹0"),
    ],
)
def test_format(paise, text):
    assert format_rupees(paise) == text
