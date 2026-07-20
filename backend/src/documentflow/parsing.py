"""Turkce fatura degerleri icin saf parser'lar (v0.1).

Bu fonksiyonlar durum (FieldStatus) uretmez; yalnizca ham metni YAPISAL olarak
parse eder. Basarisizlikta None doner (parse edilememe normal bir sonuctur,
istisna degildir). Ham metni FieldValue durumuna cevirmek extraction katmaninin
isidir (T6).
"""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

_NUMBER_RE = re.compile(r"^\d+(\.\d+)?$")
_DATE_RE = re.compile(r"^(\d{2})([./-])(\d{2})\2(\d{4})$")

# Kaldirilacak bosluk turleri: ASCII bosluk ve non-breaking space (NBSP, U+00A0).
_SPACE_CHARS = (" ", chr(0xA0))
# Temizlenecek para birimi isaretleri: TL sembolu (U+20BA) ve TL/TRY son ekleri.
_CURRENCY_SYMBOL = chr(0x20BA)
_CURRENCY_SUFFIXES = ("TRY", "TL")


def parse_tr_number(s: str | None) -> Decimal | None:
    """Turkce sayi bicimini Decimal'a cevirir ('.' binlik, ',' ondalik).

    Destekler: 1.234,56 - '... TL'/'... TRY' - leading para sembolu - '%20'/'20%'
    - negatif (-) - bosluk ve NBSP. Turkce konvansiyonu disindaki her sey None
    doner. Yapisal parse'tir; deger araligi/mantik kontrolu (business) yapmaz.
    """
    if s is None:
        return None
    text = s.strip()
    if not text:
        return None
    # Bosluk ve NBSP (binlik ayiraci ya da susleme) temizlenir.
    for space in _SPACE_CHARS:
        text = text.replace(space, "")
    # Para sembolu ve TL/TRY son eki.
    text = text.replace(_CURRENCY_SYMBOL, "")
    upper = text.upper()
    for suffix in _CURRENCY_SUFFIXES:
        if upper.endswith(suffix):
            text = text[: -len(suffix)]
            break
    # Yuzde isareti (KDV orani).
    text = text.replace("%", "")
    if not text:
        return None
    # Isaret.
    negative = False
    if text[0] in "+-":
        negative = text[0] == "-"
        text = text[1:]
    # Turkce: '.' binlik ayiraci kaldirilir, ',' ondalik noktaya cevrilir.
    text = text.replace(".", "").replace(",", ".")
    if not _NUMBER_RE.match(text):
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    return -value if negative else value


def parse_tr_date(s: str | None) -> date | None:
    """GG.AA.YYYY tarihini date'e cevirir (ayirac . / -, 4 haneli yil).

    Yapisal olarak gecersiz tarih (or. 13. ay) None doner. ISO, metinsel ay ve
    2 haneli yil v0.1 kapsami disidir.
    """
    if s is None:
        return None
    match = _DATE_RE.match(s.strip())
    if match is None:
        return None
    day, _sep, month, year = match.groups()
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None
