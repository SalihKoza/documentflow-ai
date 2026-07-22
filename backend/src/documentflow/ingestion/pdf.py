"""V1.0 PDF kabul kontrolleri (saf; dosya sistemi ve ag erisimi yok).

V1.0 kapsami YALNIZCA metin katmanli dijital PDF'tir (PROJECT_BRIEF §4). Taranmis
belge, goruntu ve OCR gerektiren her sey V1.1'e ertelenmistir. Bu modul kapsam
disi belgeyi ZINCIRIN BASINDA ve GORUNUR bicimde reddeder: sessizce kabul edilip
sagalayiciya gonderilmez, boylece "cikarim kotu calisti" ile "belge kapsam disi"
karistirilmaz.

Girdi baytlardir; cagiran dosyayi okumaktan sorumludur.
"""

from enum import StrEnum
from io import BytesIO

from pydantic import BaseModel, ConfigDict, model_validator
from pypdf import PdfReader

# PDF dosyalarinin zorunlu imzasi.
_PDF_MAGIC = b"%PDF-"

# Tek sayfali/yonetilebilir kapsamli fatura icin fazlasiyla genis bir ust sinir.
DEFAULT_MAX_BYTES = 20 * 1024 * 1024

# Bu esigin altinda cikarilabilir karakter varsa belge "metin katmani yok" sayilir.
# Taranmis PDF'ler genelde sifir karakter dondurur; esik, bos sayfa ustbilgisi gibi
# birkac karakterlik gurultuye karsi kucuk bir pay birakir.
DEFAULT_MIN_TEXT_CHARACTERS = 32


class PdfRejectionReason(StrEnum):
    """Bir belgenin neden V1.0 kapsaminda islenemedigi."""

    not_pdf = "not_pdf"
    too_large = "too_large"
    encrypted = "encrypted"
    no_text_layer = "no_text_layer"
    unreadable = "unreadable"


class PdfInspection(BaseModel):
    """Kabul karari ve gozlenen belge ozellikleri.

    Invariant: `accepted` ANCAK VE ANCAK `reason is None`.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    accepted: bool
    reason: PdfRejectionReason | None = None
    page_count: int | None = None
    text_character_count: int | None = None

    @model_validator(mode="after")
    def _check_reason_presence(self) -> "PdfInspection":
        if self.accepted and self.reason is not None:
            raise ValueError("accepted=True iken reason None olmalidir")
        if not self.accepted and self.reason is None:
            raise ValueError("accepted=False icin reason zorunludur")
        return self


def _reject(
    reason: PdfRejectionReason,
    *,
    page_count: int | None = None,
    text_character_count: int | None = None,
) -> PdfInspection:
    return PdfInspection(
        accepted=False,
        reason=reason,
        page_count=page_count,
        text_character_count=text_character_count,
    )


def inspect_pdf(
    data: bytes,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    min_text_characters: int = DEFAULT_MIN_TEXT_CHARACTERS,
) -> PdfInspection:
    """Baytlarin V1.0 kapsaminda islenebilir bir PDF olup olmadigini belirler.

    Kontrol sirasi ucuzdan pahaliya: imza -> boyut -> ayristirma -> sifreleme ->
    metin katmani. Boylece cok buyuk veya PDF olmayan bir govde hic ayristirilmaz.
    """
    if not data.startswith(_PDF_MAGIC):
        return _reject(PdfRejectionReason.not_pdf)
    if len(data) > max_bytes:
        return _reject(PdfRejectionReason.too_large)

    # pypdf bozuk girdide cok cesitli istisnalar firlatir; hepsi ayni domain
    # sonucuna (unreadable) cevrilir.
    try:
        reader = PdfReader(BytesIO(data))
    except Exception:  # noqa: BLE001 - bozuk PDF tek bir domain sonucuna cevrilir
        return _reject(PdfRejectionReason.unreadable)

    if reader.is_encrypted:
        return _reject(PdfRejectionReason.encrypted)

    try:
        page_count = len(reader.pages)
        text_characters = sum(len((page.extract_text() or "").strip()) for page in reader.pages)
    except Exception:  # noqa: BLE001 - ayristirilamayan sayfa yapisi
        return _reject(PdfRejectionReason.unreadable)

    if page_count == 0:
        return _reject(PdfRejectionReason.unreadable, page_count=0)
    if text_characters < min_text_characters:
        return _reject(
            PdfRejectionReason.no_text_layer,
            page_count=page_count,
            text_character_count=text_characters,
        )

    return PdfInspection(
        accepted=True,
        reason=None,
        page_count=page_count,
        text_character_count=text_characters,
    )
