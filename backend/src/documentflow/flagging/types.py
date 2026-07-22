"""Insan denetimi yonlendirme (flagging) sozlesmesi.

PROJECT_BRIEF §5'in dogrudan uygulamasi: bir alanin review'a gitmesi LLM'in kendi
urettigi confidence degerine DEGIL, deterministik sinyallere dayanir. Bu modulde
hicbir olasilik, yuzde veya skor alani yoktur ve olmamalidir (testle kilitli).

Her flag alti soruyu yanitlar: hangi alan (`field_path`), hangi sinyal
(`signal_code`), ne kadar ciddi (`severity`), neden (`reason`), hangi kuraldan
geldi (`originating_rule`), kullanici ne yapmali (`suggested_action`).
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class FlagSignal(StrEnum):
    """Bir flag'i tetikleyen deterministik sinyal turu."""

    # Alan durumu kaynakli (extraction ciktisindan).
    field_missing = "field_missing"
    field_unreadable = "field_unreadable"
    parse_failure = "parse_failure"
    # Validation kurallari kaynakli (ruleset 0.1).
    identifier_format = "identifier_format"
    identifier_checksum = "identifier_checksum"
    invoice_number_format = "invoice_number_format"
    kdv_rate_out_of_scope = "kdv_rate_out_of_scope"
    header_arithmetic = "header_arithmetic"
    line_sum_mismatch = "line_sum_mismatch"
    line_arithmetic = "line_arithmetic"
    # Kapsam disi/desteklenmeyen yapi.
    unsupported_scope_structure = "unsupported_scope_structure"
    # Katalogda siniflandirilmamis bir validation kurali tetiklendi. Ruleset 0.1'de
    # kullanilmaz (test bunu dogrular); ileride kural eklenip burasi guncellenmezse
    # bulgunun SESSIZCE DUSMESINI onler.
    validation_finding = "validation_finding"


class FlagSeverity(StrEnum):
    """Flag'in ciddiyeti.

    `blocking` deterministik bir celiskiden gelir (validation `error`): veri kesin
    yanlistir ve otomatik onay/export'u bloklamasi beklenir. `review` bir sapma
    veya eksikliktir: insan bakmalidir, fakat "kesin yanlis" iddiasi yoktur.
    """

    blocking = "blocking"
    review = "review"


class ReviewAction(StrEnum):
    """Kullanicidan beklenen somut duzeltme eylemi."""

    verify_field_against_document = "verify_field_against_document"
    correct_identifier = "correct_identifier"
    confirm_invoice_number = "confirm_invoice_number"
    confirm_vat_rate = "confirm_vat_rate"
    confirm_totals = "confirm_totals"
    manual_entry_out_of_scope = "manual_entry_out_of_scope"


class ReviewFlag(BaseModel):
    """Tek bir alan icin insan denetimi yonlendirme kaydi."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    # `documentflow.validation` ile ayni adres bicimi: "header.<alan>",
    # "kalemler", "kalemler[<i>].<alan>". Yolda ".value" bulunmaz.
    field_path: str
    signal_code: FlagSignal
    severity: FlagSeverity
    # Insan-okunur aciklama. STABIL KONTRAT DEGILDIR; tuketiciler `signal_code`
    # uzerinden ayristirir.
    reason: str
    # Kaynak validation kuralinin kimligi; alan durumu kaynakli flag'lerde None.
    originating_rule: str | None
    suggested_action: ReviewAction
