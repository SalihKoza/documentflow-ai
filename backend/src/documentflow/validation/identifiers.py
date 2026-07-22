"""VKN ve TCKN icin saf bicim ve checksum fonksiyonlari.

Bu modul semadan (Invoice/FieldValue) ve framework'ten tamamen bagimsizdir:
girdi `str`, cikti `bool`. Bicim kontrolu ile checksum kontrolu bilincli olarak
AYRI fonksiyonlardir; kural katmani "yanlis uzunluk" ile "checksum tutmuyor"
hatalarini farkli rule ID'lerle raporlayabilsin diye.

Girdi TEMIZLENMEZ: bosluk, nokta veya "VKN:" gibi etiketlerin ayiklanmasi
extraction katmaninin isidir (D-020 ile ayni ayrim). Buraya gelen `value`,
FieldValue.value'dur ve zaten normalize edilmis olmalidir.
"""

import re

# ASCII rakam kisitlamasi bilinclidir: str.isdigit() Arap-Hint rakamlarinda
# ("١٢٣") True doner ve int() bunlari cevirir; bu da gecerli
# gorunen fakat belgede olmayan bir kimlik numarasi anlamina gelirdi.
_VKN_FORMAT = re.compile(r"\A[0-9]{10}\Z")
_TCKN_FORMAT = re.compile(r"\A[1-9][0-9]{10}\Z")


def has_vkn_format(value: str) -> bool:
    """VKN bicim kontrolu: tam 10 ASCII rakam."""
    return _VKN_FORMAT.match(value) is not None


def has_tckn_format(value: str) -> bool:
    """TCKN bicim kontrolu: tam 11 ASCII rakam ve ilk hane sifir olamaz."""
    return _TCKN_FORMAT.match(value) is not None


def vkn_checksum_ok(value: str) -> bool:
    """VKN (10 hane) checksum dogrulamasi.

    Ilk dokuz hane, soldan saga agirliklandirilarak onuncu (kontrol) haneyi
    uretir. `has_vkn_format(value)` on kosuldur; saglanmazsa `ValueError`
    yukselir (bu bir programlama hatasidir, gecersiz veri degil).
    """
    if not has_vkn_format(value):
        raise ValueError("vkn_checksum_ok yalnizca 10 haneli rakam dizisi kabul eder")
    digits = [ord(c) - 48 for c in value]
    total = 0
    for index in range(9):
        shifted = (digits[index] + 9 - index) % 10
        # shifted == 9 dalinda 2**k carpani mod 9'da sifirlanacagindan deger
        # dogrudan eklenir; algoritmanin tanimli ozel durumudur.
        total += shifted if shifted == 9 else (shifted * 2 ** (9 - index)) % 9
    return (10 - total % 10) % 10 == digits[9]


def tckn_checksum_ok(value: str) -> bool:
    """TCKN (11 hane) checksum dogrulamasi.

    10. hane: (tek konumlarin toplami * 7 - cift konumlarin toplami) mod 10.
    11. hane: ilk on hanenin toplami mod 10.
    `has_tckn_format(value)` on kosuldur; saglanmazsa `ValueError` yukselir.
    """
    if not has_tckn_format(value):
        raise ValueError("tckn_checksum_ok yalnizca 11 haneli, sifirla baslamayan dizi kabul eder")
    digits = [ord(c) - 48 for c in value]
    odd_sum = digits[0] + digits[2] + digits[4] + digits[6] + digits[8]
    even_sum = digits[1] + digits[3] + digits[5] + digits[7]
    tenth = (odd_sum * 7 - even_sum) % 10
    eleventh = sum(digits[:10]) % 10
    return tenth == digits[9] and eleventh == digits[10]
