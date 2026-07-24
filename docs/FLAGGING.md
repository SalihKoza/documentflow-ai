# DocumentFlow AI — Deterministik Review Flagging

```text
Flag contract:    v0.1
Ruleset version:  0.1
Schema version:   v0.1 (FROZEN — 2026-07-23, D-058)
Status:           DRAFT
```

Bu belge, çıkarılan bir faturanın hangi alanlarının **insan denetimine yönlendirileceğini**
belirleyen katmanı tanımlar. Katman **kod olarak uygulanmıştır**
(`backend/src/documentflow/flagging/`); bu belge o uygulamayı birebir açıklar.

Bu, PROJECT_BRIEF §5'in doğrudan uygulamasıdır:

> Bu projede, **LLM'in kendi ürettiği confidence skoru ana güven kaynağı olarak
> kullanılmayacaktır.**

---

## 1. Giriş noktası

```python
from documentflow.flagging import build_review_flags

flags = build_review_flags(invoice, report, parse_failures=result.parse_failures)
```

Saftır: I/O yok, global durum yok, aynı girdi → aynı çıktı. Girdi yalnızca **iki deterministik
kaynaktan** gelir:

1. **Çıkarım çıktısının alan durumları** — `FieldStatus` (`missing` / `unreadable`) ve extraction
   mapping katmanının bildirdiği `parse_failures` (bkz. [`EXTRACTION.md`](EXTRACTION.md) §5).
2. **Validation raporu** — `documentflow.validation` bulguları ve değerlendirilemeyen kural
   kayıtları (bkz. [`VALIDATION.md`](VALIDATION.md)).

Model tabanlı hiçbir sinyal kullanılmaz.

---

## 2. `ReviewFlag` sözleşmesi

Her flag altı soruyu yanıtlar:

| Alan | Anlam |
| ---- | ----- |
| `field_path` | Hangi alan. Validation ile **aynı adres biçimi**: `header.<alan>`, `kalemler`, `kalemler[<i>].<alan>`. Yolda `.value` bulunmaz. |
| `signal_code` | Hangi deterministik sinyal (§3). **Tüketiciler bu alana göre ayrıştırır.** |
| `severity` | `blocking` veya `review` (§4). |
| `reason` | Neden — insan-okunur açıklama. **Stabil kontrat değildir.** |
| `originating_rule` | Kaynak validation kuralının kimliği; alan durumu kaynaklı flag'lerde `None`. |
| `suggested_action` | Kullanıcıdan beklenen somut düzeltme eylemi (§5). |

---

## 3. Sinyal kataloğu

### Alan durumu kaynaklı (çıkarım çıktısından)

| `signal_code` | Tetikleyici | Ayrım neden önemli |
| ------------- | ----------- | ------------------ |
| `field_missing` | `FieldStatus.missing` | Alan belgede **hiç yoktu** — kullanıcı belgeye bakıp girmeli |
| `field_unreadable` | `FieldStatus.unreadable` | Alan vardı ama **okunamadı** — bozuk/anlaşılmaz metin |
| `parse_failure` | Mapper `ok`→`unreadable` düşürdü | Model alanı **okuduğunu söyledi**, fakat değer beklenen biçimde çevrilemedi. Bu bir *format* sorunudur; belge okunaklı olabilir. |

`parse_failure`, aynı alan için `field_unreadable`'ın **yerini alır** — iki flag üretilmez.

### Validation kaynaklı (ruleset 0.1)

| `signal_code` | Kaynak kural(lar) |
| ------------- | ----------------- |
| `identifier_format` | `VKN-001`, `TCKN-001`, `ID-001` |
| `identifier_checksum` | `VKN-002`, `TCKN-002` |
| `invoice_number_format` | `FNO-001` |
| `kdv_rate_out_of_scope` | `KDV-001` |
| `header_arithmetic` | `ARITH-001` |
| `line_sum_mismatch` | `ARITH-002` |
| `line_arithmetic` | `ARITH-003` |

### Kapsam dışı yapı

| `signal_code` | Tetikleyici |
| ------------- | ----------- |
| `unsupported_scope_structure` | `ARITH-002` değerlendirilemedi, neden `no_line_items` (kalem tablosu bulundu fakat satır çıkarılamadı) |

### Katalog dışı yakalayıcı

| `signal_code` | Tetikleyici |
| ------------- | ----------- |
| `validation_finding` | Katalogda sınıflandırılmamış bir kural tetiklendi |

Ruleset 0.1'de **kullanılmaz** (bir test bunu doğrular). Var olma nedeni: ileride bir kural
eklenip bu katalog güncellenmezse bulgunun **sessizce düşmesini** önlemek. Yönlendirme
sinyalinin sessizce kaybolması, yanlış sinyal üretmekten daha tehlikelidir.

---

## 4. Severity

| Değer | Anlam |
| ----- | ----- |
| `blocking` | Validation `error`'ından gelir: deterministik bir çelişki var, **veri kesin yanlış**. Otomatik onay/export'u bloklaması beklenir. |
| `review` | Validation `warning`'i veya alan durumu kaynaklı. İnsan bakmalıdır, fakat "kesin yanlış" iddiası yapılmaz. |

Alan durumu kaynaklı flag'ler (`field_missing`, `field_unreadable`, `parse_failure`) her zaman
`review`'dur: eksik bir alan bir **çelişki** değil, bir **boşluktur**.

---

## 5. Önerilen eylemler

| `suggested_action` | Ne zaman |
| ------------------ | -------- |
| `verify_field_against_document` | Alan durumu kaynaklı tüm flag'ler |
| `correct_identifier` | VKN/TCKN biçim ve checksum |
| `confirm_invoice_number` | Fatura numarası biçim sapması |
| `confirm_vat_rate` | Kapsam dışı KDV oranı |
| `confirm_totals` | Aritmetik kurallar |
| `manual_entry_out_of_scope` | Desteklenmeyen yapı |

---

## 6. Deterministik sıra

Sıra **inşa yoluyla** sabittir; rapor sonradan sıralanmaz:

1. Header alanlarının durum flag'leri — `InvoiceHeader` **bildirim sırasında**
2. `kalemler` container'ının durum flag'i
3. Satır alanlarının durum flag'leri — **index artan**, satır içinde `LineItem` bildirim sırasında
4. Validation bulguları — **rapor sırasında** (P3'ün kendi deterministik sırası)
5. Kapsam dışı yapı kayıtları

Alan sırası hardcode edilmez; `model_fields` üzerinden okunur — şema değişirse sıra otomatik
olarak şemayı izler.

---

## 7. Deduplication

Anahtar: **`(field_path, signal_code, originating_rule)`**. Aynı üçlü ikinci kez üretilirse
düşürülür (ilk kalır).

Ayrıca iki yapısal kural çift raporlamayı en baştan engeller:

- **Değerlendirilemeyen kurallardan yalnızca kapsam dışı yapı sinyali çıkarılır.**
  `missing`/`unreadable` nedenli `not_evaluated` kayıtları flag üretmez — o alan zaten bir alan
  durumu flag'i almıştır. (P3'teki "kaskad atlamalar kaydedilmez" kuralının aynısı.)
- **`parse_failure`, `field_unreadable`'ın yerini alır** (§3).

---

## 8. Confidence yasağı

- `ReviewFlag` üzerinde **hiçbir** olasılık, yüzde veya skor alanı yoktur.
- Model kaynaklı bir confidence değeri zaten extraction katmanında reddedilir
  ([`EXTRACTION.md`](EXTRACTION.md) §3.2).
- v0.1'de **tek bir birleşik risk skoru da üretilmez.** PROJECT_BRIEF §5 `risk_level` gibi bir
  özet kavramı mümkün kılar fakat zorunlu tutmaz; `ValidationReport.review_required` zaten
  "bakılmalı mı" sorusunu yanıtlıyor ve `severity` "ne kadar ciddi" sorusunu yanıtlıyor. Üçüncü
  bir türetilmiş sayı bugün hiçbir soruyu yanıtlamıyor.
- İleride bir skor eklenirse **tamamen deterministik** olmalı (yalnızca sinyal sayıları ve
  severity'lerden hesaplanmalı) ve kalibre edilmiş bir olasılık gibi sunulmamalıdır.

Bu yasak testlerle kilitlenmiştir (`ReviewFlag.model_fields` kümesi ve serileştirilmiş çıktıda
`confidence`/`probability`/`score` aranması).

---

## 9. Bilinen sınırlar

- **İskonto ve tevkifat tanınamaz.** Şemada `iskonto`/`tevkifat` alanı yoktur (D-018), bu yüzden
  `unsupported_scope_structure` bu yapıları **tespit edemez**; yalnızca gözlenebilir olanı
  (kalem tablosu var, satır çıkarılamadı) kapsar. İndirimli bir fatura, aritmetik kurallar
  tuttuğu için `blocking` flag üretir ve neden kapsam dışı olduğunu söylemez.
- **Yuvarlama toleransı yok.** Kuruş yuvarlaması yapılmış satırlar `line_arithmetic` false
  positive üretir (D-038'in bilinen bedeli).
- **Alan önceliklendirme yok.** Flag'ler sırayla verilir; "önce şuna bak" türü bir sıralama
  üretilmez.
- **Metin alanları için içerik kontrolü yok.** `satici_unvan` gibi serbest metinler yalnızca
  durum düzeyinde flag alır.
- **Şema FROZEN'dır** (D-058): freeze'de alan adları değişmediği için `field_path` değerleri sabittir.

---

## 10. Testler

`backend/tests/flagging/test_build_review_flags.py` — sentetik fatura fixture'ları validation
testleriyle **paylaşılır** (`tests/validation/_fixtures.py`), böylece iki katman aynı veriyi
görür.

Kapsam: temiz faturada sıfır flag · her alan durumu sinyali · `parse_failure`'ın
`field_unreadable`'ın yerini alması · her validation kuralının doğru sinyale eşlenmesi · severity
eşlemesi · kapsam dışı yapı · çift raporlama olmaması · sabit sıra · tekrar çalıştırmada birebir
aynı çıktı · katalog dışı yakalayıcının ruleset 0.1'de kullanılmaması · confidence benzeri alan
bulunmaması.

---

## İlgili belgeler

- Extraction sözleşmesi: [`EXTRACTION.md`](EXTRACTION.md)
- Validation kuralları: [`VALIDATION.md`](VALIDATION.md)
- Şema kontratı: [`SCHEMA.md`](SCHEMA.md)
- Karar günlüğü: [`DECISIONS.md`](DECISIONS.md)
- Ürün kapsamı: [`PROJECT_BRIEF.md`](../PROJECT_BRIEF.md) §5
