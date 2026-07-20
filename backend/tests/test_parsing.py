"""Turkce sayi/tarih parser testleri (v0.1 kapsami)."""

from datetime import date
from decimal import Decimal

import pytest

from documentflow.parsing import parse_tr_date, parse_tr_number

_NBSP = chr(0xA0)
_TL = chr(0x20BA)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1.234,56", Decimal("1234.56")),
        ("1.234,56 TL", Decimal("1234.56")),
        ("1.234,56 TRY", Decimal("1234.56")),
        (_TL + "1.234,56", Decimal("1234.56")),
        ("%20", Decimal("20")),
        ("20%", Decimal("20")),
        ("-1.234,56", Decimal("-1234.56")),
        ("1 234,56", Decimal("1234.56")),
        ("1" + _NBSP + "234,56", Decimal("1234.56")),
        ("0", Decimal("0")),
        ("1.234.567,89", Decimal("1234567.89")),
    ],
)
def test_parse_tr_number_valid(text: str, expected: Decimal) -> None:
    assert parse_tr_number(text) == expected


@pytest.mark.parametrize(
    "text",
    ["", "   ", "abc", "1,2,3", "--5", None],
)
def test_parse_tr_number_invalid(text: str | None) -> None:
    assert parse_tr_number(text) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("15.03.2025", date(2025, 3, 15)),
        ("15/03/2025", date(2025, 3, 15)),
        ("15-03-2025", date(2025, 3, 15)),
    ],
)
def test_parse_tr_date_valid(text: str, expected: date) -> None:
    assert parse_tr_date(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "31.13.2025",
        "32.01.2025",
        "5.3.2025",
        "2025-03-15",
        "15.03-2025",
        "15.03.25",
        "abc",
        "",
        None,
    ],
)
def test_parse_tr_date_invalid(text: str | None) -> None:
    assert parse_tr_date(text) is None
