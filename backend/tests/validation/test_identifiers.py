"""VKN ve TCKN bicim/checksum fonksiyon testleri.

Tum kimlik numaralari SENTETIKTIR: gercek bir belgeden alinmamis, checksum
algoritmasindan turetilmistir ve hicbir kisi/kurum ile iliskilendirilemez.
Vektorlerin sessizce curumesini engellemek icin, sabit vektorlerin yani sira
"gecerli kontrol hanesi tektir" ozelligi de dogrulanir.
"""

import pytest

from documentflow.validation import (
    has_tckn_format,
    has_vkn_format,
    tckn_checksum_ok,
    vkn_checksum_ok,
)

_DIGITS = "0123456789"

# Checksum'i gecerli sentetik VKN'ler. "1234567890" kontrol hanesinin 0 ciktigi
# (total % 10 == 0) dali; "0000000001" ve "0123456789" algoritmadaki shifted == 9
# ozel dalini kapsar.
VALID_VKNS = [
    "1234567890",
    "0000000001",
    "1111111114",
    "9876543217",
    "0123456789",
    "5555555553",
]

# Checksum'i gecerli sentetik TCKN'ler. "19090909018" ara toplamin mod oncesi
# NEGATIF ciktigi (-29) dali; "99999999990" 11. hanenin 0 ciktigi dali.
VALID_TCKNS = [
    "10000000146",
    "12345678950",
    "99999999990",
    "24681357994",
    "10000000078",
    "91827364550",
    "19090909018",
]


# --- Bicim kontrolu ------------------------------------------------------------------


@pytest.mark.parametrize("value", ["1234567890", "0000000000", "9999999999"])
def test_has_vkn_format_accepts_ten_ascii_digits(value: str) -> None:
    assert has_vkn_format(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "123456789",  # 9 hane
        "12345678901",  # 11 hane
        "",  # bos
        "12345678a0",  # harf
        "123456 789",  # bosluk
        "123456789 ",  # sondaki bosluk kirpilmaz
        "-123456789",  # isaret
        "12345678.0",  # nokta
        "١٢٣٤٥٦٧٨٩٠",  # Arap-Hint rakamlari
    ],
)
def test_has_vkn_format_rejects(value: str) -> None:
    assert has_vkn_format(value) is False


@pytest.mark.parametrize("value", ["10000000146", "19999999999", "99999999999"])
def test_has_tckn_format_accepts_eleven_ascii_digits(value: str) -> None:
    assert has_tckn_format(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "1000000014",  # 10 hane
        "100000001466",  # 12 hane
        "",  # bos
        "00000000146",  # ilk hane sifir olamaz
        "0000000000 ",  # ilk hane sifir + bosluk
        "1000000014a",  # harf
        "1000000 146",  # bosluk
        "١٠٠٠٠٠٠٠١٤٦",  # Arap-Hint
    ],
)
def test_has_tckn_format_rejects(value: str) -> None:
    assert has_tckn_format(value) is False


def test_unicode_digits_are_not_treated_as_digits() -> None:
    # str.isdigit() bu dizide True doner ve int() onu cevirir; ASCII kisitlamasi
    # olmasaydi belgede bulunmayan bir kimlik gecerli gorunebilirdi.
    arabic_indic = "١٢٣٤٥٦٧٨٩٠"
    assert arabic_indic.isdigit() is True
    assert has_vkn_format(arabic_indic) is False


# --- VKN checksum --------------------------------------------------------------------


@pytest.mark.parametrize("value", VALID_VKNS)
def test_vkn_checksum_accepts_valid_vectors(value: str) -> None:
    assert vkn_checksum_ok(value) is True


@pytest.mark.parametrize("value", VALID_VKNS)
def test_vkn_checksum_rejects_mutated_check_digit(value: str) -> None:
    mutated = value[:9] + str((int(value[9]) + 1) % 10)
    assert vkn_checksum_ok(mutated) is False


@pytest.mark.parametrize("prefix", [value[:9] for value in VALID_VKNS])
def test_exactly_one_vkn_check_digit_is_valid(prefix: str) -> None:
    # Kontrol hanesi tek olmali: algoritma degisirse bu ozellik once bozulur.
    accepted = [digit for digit in _DIGITS if vkn_checksum_ok(prefix + digit)]
    assert len(accepted) == 1


@pytest.mark.parametrize("value", ["123456789", "12345678901", "", "12345678a0"])
def test_vkn_checksum_requires_valid_format(value: str) -> None:
    with pytest.raises(ValueError):
        vkn_checksum_ok(value)


# --- TCKN checksum -------------------------------------------------------------------


@pytest.mark.parametrize("value", VALID_TCKNS)
def test_tckn_checksum_accepts_valid_vectors(value: str) -> None:
    assert tckn_checksum_ok(value) is True


@pytest.mark.parametrize("value", VALID_TCKNS)
def test_tckn_checksum_rejects_mutated_eleventh_digit(value: str) -> None:
    mutated = value[:10] + str((int(value[10]) + 1) % 10)
    assert tckn_checksum_ok(mutated) is False


@pytest.mark.parametrize("value", VALID_TCKNS)
def test_tckn_checksum_rejects_mutated_tenth_digit(value: str) -> None:
    mutated = value[:9] + str((int(value[9]) + 1) % 10) + value[10]
    assert tckn_checksum_ok(mutated) is False


@pytest.mark.parametrize("prefix", [value[:9] for value in VALID_TCKNS])
def test_exactly_one_tckn_check_digit_pair_is_valid(prefix: str) -> None:
    accepted = [
        tenth + eleventh
        for tenth in _DIGITS
        for eleventh in _DIGITS
        if tckn_checksum_ok(prefix + tenth + eleventh)
    ]
    assert len(accepted) == 1


def test_tckn_checksum_handles_negative_intermediate() -> None:
    # (tek toplami * 7 - cift toplami) = -29; Python mod'u negatifte de dogrudur.
    assert tckn_checksum_ok("19090909018") is True


@pytest.mark.parametrize("value", ["1000000014", "100000001466", "", "00000000146"])
def test_tckn_checksum_requires_valid_format(value: str) -> None:
    with pytest.raises(ValueError):
        tckn_checksum_ok(value)
