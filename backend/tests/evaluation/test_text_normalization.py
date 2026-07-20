"""normalize_for_comparison() testleri - Turkce case, Unicode ve whitespace.

Tum test degerleri sentetiktir (gercek sirket adi, VKN/TCKN veya fatura icermez).
Combining dot ve NBSP gibi gorunmez karakterler named escape ile kurulur.
"""

import unicodedata

import pytest

from documentflow.evaluation import normalize_for_comparison

_DOT = "\N{COMBINING DOT ABOVE}"  # U+0307
_NBSP = "\N{NO-BREAK SPACE}"  # U+00A0


# --- Turkce buyuk/kucuk harf ---------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("IŞIK", "ışık"),
        ("Işık", "ışık"),
        ("İSTANBUL", "istanbul"),
        ("İstanbul", "istanbul"),
        ("ĞÜŞİÖÇ", "ğüşiöç"),
    ],
)
def test_turkish_case(value: str, expected: str) -> None:
    assert normalize_for_comparison(value) == expected


# --- Unicode canonical equivalence (NFD ve NFC ayni sonuc) ---------------------------


@pytest.mark.parametrize("char", ["İ", "Ş", "Ğ", "Ö", "Ü", "Ç"])
def test_nfc_nfd_equivalence(char: str) -> None:
    precomposed = unicodedata.normalize("NFC", char)
    decomposed = unicodedata.normalize("NFD", char)
    # Gercekten farkli kod nokta dizileri olmali; aksi halde test bir sey kanitlamaz.
    assert precomposed != decomposed
    assert normalize_for_comparison(precomposed) == normalize_for_comparison(decomposed)


# --- Combining dot -------------------------------------------------------------------


def test_combining_dot_variants_collapse_to_i() -> None:
    variants = ["İ", "I" + _DOT, "i" + _DOT]
    results = [normalize_for_comparison(v) for v in variants]
    assert results == ["i", "i", "i"]
    # Ciktida gereksiz combining dot kalmamali.
    for result in results:
        assert _DOT not in result


# --- Whitespace ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("  abc  ", "abc"),
        ("a  b", "a b"),
        ("a\tb", "a b"),
        ("a\nb", "a b"),
        ("a\r\nb", "a b"),
        ("a" + _NBSP + "b", "a b"),
        ("a \t\n b", "a b"),
        ("  ABC\t\nYazılım  ", "abc yazılım"),
        ("   ", ""),
        (" \t\n" + _NBSP, ""),
    ],
)
def test_whitespace(value: str, expected: str) -> None:
    assert normalize_for_comparison(value) == expected


# --- Noktalama ve Turkce harf korunumu -----------------------------------------------


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("A.Ş.", "AŞ"),
        ("Ltd. Şti.", "Ltd Şti"),
        ("ABC-Yazılım", "ABC Yazılım"),
    ],
)
def test_punctuation_preserved_so_values_differ(left: str, right: str) -> None:
    assert normalize_for_comparison(left) != normalize_for_comparison(right)


def test_punctuation_positive() -> None:
    assert normalize_for_comparison("A.Ş.") == "a.ş."


def test_turkish_letters_not_transliterated() -> None:
    assert normalize_for_comparison("ŞĞÇÖÜ") == "şğçöü"
    assert normalize_for_comparison("Ş") == "ş"
    assert normalize_for_comparison("Ş") != "s"


# --- Determinizm ve idempotence ------------------------------------------------------

_SAMPLES = ["İstanbul A.Ş.", "  IŞIK  Ltd. Şti. ", "ABC-Yazılım", "ĞÜŞİÖÇ", "i" + _DOT]


@pytest.mark.parametrize("value", _SAMPLES)
def test_deterministic(value: str) -> None:
    assert normalize_for_comparison(value) == normalize_for_comparison(value)


@pytest.mark.parametrize("value", _SAMPLES)
def test_idempotent(value: str) -> None:
    once = normalize_for_comparison(value)
    assert normalize_for_comparison(once) == once


# --- Tip davranisi -------------------------------------------------------------------


@pytest.mark.parametrize("bad", [None, 123, b"bytes"])
def test_non_str_raises_type_error(bad: object) -> None:
    with pytest.raises(TypeError):
        normalize_for_comparison(bad)  # type: ignore[arg-type]
