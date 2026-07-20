"""Turkce metin karsilastirma normalizasyonu (evaluation katmani).

`docs/EVALUATION.md` §3 ve karar D-027'deki karsilastirma kontratinin saf
uygulamasidir. Bu fonksiyon yalnizca ground-truth ve extraction metin degerlerini
KARSILASTIRMADAN once normalize eder; degerleri saklamaz, extraction/parser akisina
girmez ve is (business) mantigi icermez.

Normalizasyon sirasi sabittir: (1) Unicode NFC, (2) Turkce buyuk/kucuk harf,
(3) whitespace. Noktalama, Turkce harfler ve diakritikler KORUNUR; accent kaldirma,
unvan kisaltmasi esitleme (A.S. == AS gibi) veya fuzzy matching YAPILMAZ.
"""

import re
import unicodedata

# Turkce buyuk -> kucuk harf eslemesi (lowercase ONCESINDE uygulanir). Python'un
# .lower()/.casefold() yontemi Turkce icin yanlistir: İ (U+0130) -> "i" + U+0307
# (gereksiz combining dot) ve I (U+0049) -> noktali "i" uretir. Dogru esleme:
# İ -> i (U+0069), I -> ı (U+0131 noktasiz).
_TR_CASE_TABLE = str.maketrans({"İ": "i", "I": "ı"})

# NFC ile birlesmeyen "i + combining dot above" dizisi (U+0069 U+0307) sade "i"ye
# indirgenir. Yalnizca bu combining dot kaldirilir; diger harflerdeki gercek
# diakritikler korunur. Named escape ile kurulur; kaynakta gorunmez karakter olmaz.
_COMBINING_DOT_ABOVE = "\N{COMBINING DOT ABOVE}"
_DOTTED_I = "i" + _COMBINING_DOT_ABOVE

# Her Unicode whitespace kosusu (tab, newline, CR, NBSP U+00A0 vb.) tek ASCII bosluga.
_WHITESPACE_RUN = re.compile(r"\s+")


def normalize_for_comparison(value: str) -> str:
    """Metin alanlarini karsilastirma icin normalize eder (saf, deterministik).

    Ayni bilgiyi tasiyan gorsel/kodlama varyantlarini esitler; anlamli farklari
    (noktalama, Turkce harfler) korur. Saftir: I/O yapmaz, locale/OS ayarina
    bagimli degildir, girdiyi degistirmez ve ayni girdi icin ayni ciktiyi verir.
    Sonuc NFC formundadir ve fonksiyon idempotenttir.

    `value` bir `str` olmalidir; `None`, `int` veya `bytes` verilirse ilk
    `unicodedata.normalize` cagrisi dogal bir `TypeError` firlatir (bilincli olarak
    ozel istisna ile sarilmaz).
    """
    # 1. Unicode canonical normalization (NFC). Decomposed "I + U+0307" gibi varyantlar
    # burada precomposed İ'ye (U+0130) toplanir; combining-dot ele alinmadan once bu
    # adim sarttir (aksi halde "I + dot" once ı'ya donusup yanlis sonuc verirdi).
    text = unicodedata.normalize("NFC", value)

    # 2. Turkce buyuk/kucuk harf: once İ/I acik eslemesi, sonra kalanlar lowercase.
    text = text.translate(_TR_CASE_TABLE)
    text = text.replace(_DOTTED_I, "i")
    text = text.lower()

    # 3. Whitespace: bosluk kosulari tek ASCII bosluga, bas/son kirpilir.
    text = _WHITESPACE_RUN.sub(" ", text).strip()

    return text
