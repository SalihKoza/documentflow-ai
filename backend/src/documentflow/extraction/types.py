"""Extraction sozlesmesi cekirdek tipleri (v0.1).

Bu modul yalnizca VERIYI tasir; sagalayici (provider) mantigi icermez. Hicbir LLM
SDK'si, FastAPI veya veritabani importu yoktur ve olmamalidir (testle kilitli).

Provider metadata (model adi, prompt surumu, latency, token, maliyet) bilincli
olarak domain modelinden AYRIDIR: `Invoice` sadece belgeden cikarilan veriyi
tasir, calisma bilgisi burada `ProviderMetadata` icinde durur. Boylece sagalayici
degistiginde domain kontrati degismez.

LLM'in kendi urettigi confidence degeri BU SOZLESMEYE GIRMEZ (PROJECT_BRIEF §5):
guven sinyali deterministik kurallardan turetilir (bkz. documentflow.flagging).
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from documentflow.schema import Invoice
from documentflow.schema.types import Numeric

# Cikarim ciktisinin hedefledigi sema kontrat surumu (Invoice.schema_version).
DEFAULT_SCHEMA_VERSION = "0.1"


class ExtractionStatus(StrEnum):
    """Bir cikarim denemesinin sonucu.

    `ok` disindaki her deger bir BASARISIZLIKTIR ve `invoice` None'dir. Sagalayici
    istisnalari disari sizmaz; adapter onlari bu degerlere cevirir.
    """

    ok = "ok"
    # Sagalayici gecerli JSON uretmedi.
    invalid_json = "invalid_json"
    # JSON gecerli fakat beklenen sozlesmeye uymuyor (eksik/fazla alan, gecersiz
    # durum degeri, yapisal invariant ihlali). `confidence` gibi beklenmeyen bir
    # alan da buraya duser: sessizce yutulmaz.
    schema_mismatch = "schema_mismatch"
    # Sagalayici tarafinda hata (rate limit, sunucu hatasi, baglanti).
    provider_error = "provider_error"
    # Istek zaman asimina ugradi.
    timeout = "timeout"
    # Sagalayici istegi reddetti.
    refused = "refused"
    # Cikti token siniri nedeniyle yarim kaldi.
    truncated = "truncated"


class ExtractionRequest(BaseModel):
    """Bir belgeyi cikarima gonderme istegi.

    Sagalayici ayari (model adi, anahtar, timeout) BU MODELDE YOKTUR; o adapter'in
    kendi yapilandirmasidir. Burada yalnizca belgeye ait bilgi bulunur.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    # Anonim/opak belge kimligi. Gercek dosya adi DEGILDIR (bkz. DATA_COLLECTION §3).
    document_id: str
    # Ham belge baytlari. repr=False: kaza eseri loglanmasini/repr'e girmesini onler.
    content: bytes = Field(repr=False)
    media_type: str = "application/pdf"
    page_count: int | None = None


class ProviderMetadata(BaseModel):
    """Cikarimi kimin, neyle ve ne maliyetle urettigi.

    Cost ve latency OLCUM NOKTALARI burasidir: adapter cagriyi monotonic saatle
    sarmalar ve sagalayicinin bildirdigi token sayilarini buraya yazar.
    Confidence/olasilik alani BULUNMAZ.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str
    model: str
    prompt_version: str
    schema_version: str = DEFAULT_SCHEMA_VERSION
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_read_input_tokens: int | None = None
    cache_creation_input_tokens: int | None = None
    # Decimal (float degil, D-017). Liste fiyatindan hesaplanan TAHMINDIR;
    # fatura gercegi degildir.
    estimated_cost_usd: Numeric | None = None
    request_id: str | None = None


class ExtractionResult(BaseModel):
    """Tek bir cikarim denemesinin tam sonucu.

    Invariant: `invoice` non-None ANCAK VE ANCAK `status == ok`. Bu, FieldValue'nun
    (D-015/D-016) yapisal invariant desenini sonuc duzeyinde tekrarlar: basarisiz
    bir cikarim "yarim" bir Invoice dondurmez.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: ExtractionStatus
    invoice: Invoice | None = None
    metadata: ProviderMetadata
    # Sagalayici `ok` dedigi halde degeri parse edilemeyen alanlarin yollari.
    # Bu alanlar `unreadable`'a dusurulmustur (sessizce tahmin edilmez).
    parse_failures: tuple[str, ...] = ()
    # Kisa, teshis amacli metin. BELGE ICERIGI ASLA BURAYA YAZILMAZ; yalnizca
    # alan yolu ve hata turu (bkz. mapping._summarize_validation_error).
    error_detail: str | None = None

    @model_validator(mode="after")
    def _check_invoice_presence(self) -> "ExtractionResult":
        if self.status is ExtractionStatus.ok:
            if self.invoice is None:
                raise ValueError("status=ok icin invoice zorunludur")
        else:
            if self.invoice is not None:
                raise ValueError("status != ok iken invoice None olmalidir")
            if self.parse_failures:
                raise ValueError("status != ok iken parse_failures bos olmalidir")
        return self
