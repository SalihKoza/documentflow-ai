"""Validation sozlesmesi cekirdek tipleri (ruleset 0.1).

Bu modul yalnizca VERIYI tasir; kural mantigi icermez (bkz. rules.py). Rapor
deterministiktir ve LLM confidence / olasilik alani ICERMEZ: insan denetimine
yonlendirme yalnizca deterministik sinyallere dayanir (PROJECT_BRIEF §5).
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, computed_field

# Kural kumesinin surumu. Kural eklenmesi/cikarilmasi veya bir kuralin anlaminin
# degismesi bu surumu artirir; sema surumunden (Invoice.schema_version) bagimsizdir.
RULESET_VERSION = "0.1"


class Severity(StrEnum):
    """Bir bulgunun kusur turu (yonlendirme sinyali degildir)."""

    # Deterministik celiski: veri kesin yanlis (checksum tutmuyor, aritmetik kimlik
    # saglanmiyor). Ileride otomatik onay/export'u bloklamasi beklenir.
    error = "error"
    # Beklenenden sapma; mesru olabilir (or. kapsam disi bir KDV orani). Insan
    # bakmalidir fakat "veri kesin yanlis" iddiasi yapilmaz.
    warning = "warning"


class NotEvaluableReason(StrEnum):
    """Bir kuralin neden hic calisamadigi (kural gecti/kaldi DEGIL)."""

    missing_field = "missing_field"
    unreadable_field = "unreadable_field"
    no_line_items = "no_line_items"


class ValidationFinding(BaseModel):
    """Calisan bir kuralin urettigi tek bulgu."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    severity: Severity
    # Bos degildir; ilk eleman anchor (UI'nin oncelikli isaretleyecegi alan).
    # Format: "header.<alan>", "kalemler", "kalemler[<i>].<alan>" (0-based index).
    # Pydantic attribute zinciri degil ALAN ADRESI oldugu icin yolda ".value" yoktur.
    field_paths: tuple[str, ...]
    # Insan-okunur tanisal metin. STABIL KONTRAT DEGILDIR: tuketiciler rule_id
    # uzerinden ayristirir, mesaj metnine bagimlanmaz.
    message: str


class NotEvaluated(BaseModel):
    """Girdisi bulunmadigi icin hic calisamamis bir kural kaydi.

    Bu bir bulgu DEGILDIR: "kural calisti ve gecti" ile "kural hic calisamadi"
    ayrimini korur. Yalnizca girdi yoklugu kaydedilir; baska bir kuralin bulgusu
    yuzunden atlanan kaskad kurallar (or. bicim hatasi nedeniyle atlanan checksum)
    burada tekrar raporlanmaz.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    # Kurali bloklayan girdi alan(lar)i; kuralin tum girdi kumesi degil.
    field_paths: tuple[str, ...]
    reason: NotEvaluableReason


class ValidationReport(BaseModel):
    """validate_invoice() ciktisi: tek bir faturanin deterministik dogrulama sonucu."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ruleset_version: str = RULESET_VERSION
    # Sira inSA YOLUYLA deterministiktir (rules.py'deki uygulama sirasi); sonradan
    # siralanmaz. Ayni (rule_id, field_paths) cifti iki kez bulunmaz.
    findings: tuple[ValidationFinding, ...] = ()
    not_evaluated: tuple[NotEvaluated, ...] = ()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def review_required(self) -> bool:
        """Insan denetimi yonlendirme sinyali (turetilmis, saklanmaz).

        v0.1'de her iki severity de review gerektirir; error/warning ayrimi
        kusurun turunu anlatir, bakilip bakilmayacagini degil.
        """
        return len(self.findings) > 0
