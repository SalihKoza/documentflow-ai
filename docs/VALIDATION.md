# DocumentFlow AI — Deterministik Validation Kuralları

```text
Ruleset version: 0.1
Schema version:  v0.1 (FROZEN — 2026-07-23, D-058)
Status:          DRAFT
```

Bu belge, çıkarılan fatura verisi üzerinde çalışan **iş (business) kuralı** katmanını tanımlar.
Katman **kod olarak uygulanmıştır** (`backend/src/documentflow/validation/`); bu belge o
uygulamayı birebir açıklar.

Amaç, PROJECT_BRIEF §5'teki karara hizmet etmektir: bir alanın insan denetimine yönlendirilmesi
**LLM'in confidence skoruna değil, deterministik sinyallere** dayanır. Bu katmanın çıktısı o
sinyallerin ta kendisidir ve **hiçbir confidence/olasılık alanı içermez.**

---

## 1. Kapsam ve sınır

| Bu katman **yapar** | Bu katman **yapmaz** |
| ------------------- | -------------------- |
| Alanlar arası matematik ve mantık kontrolü | Yapısal invariant kontrolü (`raw`/`value`/`status` tutarlılığı) |
| VKN/TCKN checksum doğrulaması | Ham metni parse etmek veya temizlemek |
| Deterministik review yönlendirme sinyali üretmek | Değer düzeltmek, tahmin etmek veya doldurmak |
| Değerlendirilemeyen kuralları kayıt altına almak | Extraction doğruluğunu ölçmek (bu `docs/EVALUATION.md`'nin işidir) |

- **Yapısal invariant'lar** (`ok` ise `value` doludur vb.) `backend/src/documentflow/schema/types.py`
  içinde Pydantic tarafından zorlanır; buraya gelen `Invoice` zaten yapısal olarak geçerlidir.
- **Girdi temizlenmez.** `"VKN: 123 456 7890"` gibi etiket/boşluk ayıklama extraction katmanının
  işidir (D-020 ile aynı ayrım). Validation, `FieldValue.value` alanını olduğu gibi değerlendirir.
- Katman **saf ve framework-bağımsızdır:** FastAPI, SQLAlchemy, psycopg veya bir LLM sağlayıcısı
  import edilmez, I/O yapılmaz, global durum tutulmaz. Bu kısıt bir testle kilitlenmiştir
  (`test_validation_package_has_no_framework_imports`).

### XSD/UBL-TR şema validation'ı ile iş kuralı validation'ı ayrımı (önemli)

Bu **XSD (şema) validation değildir.**

| | XSD / UBL-TR şema validation | Bu katman (iş kuralı validation) |
| --- | --- | --- |
| Girdi | e-Fatura **XML** belgesi | Çıkarılmış `Invoice` nesnesi (PDF metin katmanından) |
| Soru | Belge, UBL-TR şemasına **yapısal** olarak uygun mu? | Belgedeki bilgi **kendi içinde tutarlı ve makul** mü? |
| Yakaladığı | Eksik zorunlu eleman, yanlış tip, geçersiz sıra | Checksum hatası, toplam tutmaması, kapsam dışı KDV oranı |
| Kaçırdığı | `3000 + 600 = 9999` — şemaya uygun, matematiği yanlış | Şemaya özgü XML yapı hataları (hiç XML görmez) |

**Yapısal uygunluk, iş doğruluğunu ima etmez.** XSD'den geçen bir e-Fatura pekâlâ tutarsız
tutarlar taşıyabilir. Ayrıca XML e-Fatura entegrasyonu MVP kapsamı dışındadır
(PROJECT_BRIEF §7); bu katman **hiçbir XML ayrıştırmaz.**

---

## 2. Sözleşme

Giriş noktası tektir:

```python
from documentflow.validation import validate_invoice

report = validate_invoice(invoice)   # Invoice -> ValidationReport
```

Fonksiyon saftır: girdiyi değiştirmez, I/O yapmaz, aynı girdi için **birebir aynı** raporu üretir.

### `ValidationReport`

| Alan | Tip | Anlam |
| ---- | --- | ----- |
| `ruleset_version` | `str` | Raporu üreten kural kümesinin sürümü (`"0.1"`). |
| `findings` | `tuple[ValidationFinding, ...]` | Çalışan kuralların ürettiği **problemler.** |
| `not_evaluated` | `tuple[NotEvaluated, ...]` | Girdisi bulunmadığı için **hiç çalışamamış** kurallar. |
| `review_required` | `bool` (türetilmiş) | `len(findings) > 0`. İnsan denetimi yönlendirme sinyali. |

### `ValidationFinding`

| Alan | Tip | Anlam |
| ---- | --- | ----- |
| `rule_id` | `str` | Kural kimliği (§3). **Tüketiciler bu alana göre ayrıştırır.** |
| `severity` | `Severity` | `error` veya `warning` (aşağıya bkz.). |
| `field_paths` | `tuple[str, ...]` | Boş değildir; **ilk eleman anchor'dır** (öncelikli işaretlenecek alan). |
| `message` | `str` | İnsan-okunur tanısal metin. **Stabil kontrat değildir**; metnine bağımlanılmaz. |

### `NotEvaluated`

| Alan | Tip | Anlam |
| ---- | --- | ----- |
| `rule_id` | `str` | Çalışamayan kural. Alan başına birden çok kural varsa **kapı (gate) kuralın** kimliği yazılır: `satici_vkn` → `VKN-001`, `alici_vkn_tckn` → `ID-001`. |
| `field_paths` | `tuple[str, ...]` | Kuralı **bloklayan** girdi alanları (kuralın tüm girdi kümesi değil). |
| `reason` | `NotEvaluableReason` | `missing_field`, `unreadable_field` veya `no_line_items`. |

### Severity ve review flag ayrımı

- **`error`** — Deterministik çelişki: veri **kesin yanlış**. Checksum tutmuyor, aritmetik kimlik
  sağlanmıyor veya kimlik numarası hiçbir geçerli biçime uymuyor. İleride otomatik onay/export'u
  bloklaması beklenir.
- **`warning`** — Beklenenden sapma; **meşru olabilir.** Kapsam dışı bir KDV oranı veya kâğıt
  fatura numara biçimi gibi. İnsan bakmalıdır, fakat "veri kesin yanlış" iddiası yapılmaz.
- **`review_required`** — Yönlendirme sinyalidir ve **türetilmiştir.** v0.1'de her iki severity de
  `review_required = True` yapar; error/warning farkı *kusurun türünü* anlatır, *bakılıp
  bakılmayacağını* değil.

> **`not_evaluated` review gerektirmez.** Değerlendirilemeyen bir kural, bulunmuş bir problem
> değildir. Alanın kendisi zaten `missing`/`unreadable` olduğu için yönlendirme sinyali
> extraction durumundan gelir; validation aynı şeyi ikinci kez raporlamaz.

### `field_path` formatı

```text
header.<alan_adi>              ör. header.satici_vkn, header.genel_toplam
kalemler                       kalem container'ı (FieldValue[list[LineItem]])
kalemler[<index>].<alan_adi>   ör. kalemler[0].satir_tutari   (index 0-tabanlı)
```

Bu bir **alan adresidir**, Pydantic attribute zinciri değildir: yolda **`.value` bulunmaz.**
Index Python liste indeksiyle aynıdır (0-tabanlı); kullanıcı arayüzü isterse 1-tabanlı gösterir.

### Deterministik sıra

Sıra **inşa yoluyla** sabittir; rapor sonradan sıralanmaz:

1. Header alan kuralları — `InvoiceHeader` bildirim sırasında: `fatura_no` → `satici_vkn` →
   `alici_vkn_tckn`
2. Header toplam aritmetiği — `ARITH-001`
3. Kalem kuralları — index **artan** sırada; her satır içinde `KDV-001`, sonra `ARITH-003`
4. İki seviyeyi bağlayan toplam — `ARITH-002`

Her kural her hedefe **bir kez** uygulanır; aynı `(rule_id, field_paths)` çifti raporda tekrar
etmez.

### `not_evaluable` davranışı

Bir kural, **girdi alanlarının hepsi `status=ok` değilse** çalışmaz ve `not_evaluated` listesine
bir kayıt düşer.

- **Reason önceliği:** bloke edenler arasında en az bir `missing` varsa `missing_field`, aksi
  halde `unreadable_field`.
- **Kaskad atlamalar kaydedilmez.** `VKN-001` biçim hatası verdiği için `VKN-002` checksum'ı
  çalışmadıysa bu `not_evaluated`'a yazılmaz — hata zaten `findings` içinde açıklanmıştır. Yalnızca
  **girdi yokluğu** kaydedilir.
- **Boş kalem listesi** (`kalemler.status == ok` fakat liste boş) `ARITH-002` için
  `no_line_items` üretir; toplam **Σ = 0 varsayılmaz.** Boş küme üzerinde toplam almak dejenere bir
  öncüldür ve extraction tabloyu bulup satır çıkaramamış olabilir; uydurma bir çelişki üretmek
  yerine durum görünür kılınır.

---

## 3. Kural kataloğu (ruleset 0.1)

| Rule ID | Girdi alan(lar)ı | Severity | Kural |
| ------- | ---------------- | -------- | ----- |
| `VKN-001` | `header.satici_vkn`, dispatch ile `header.alici_vkn_tckn` | `error` | Tam **10 ASCII rakam** |
| `VKN-002` | aynı | `error` | **VKN checksum** (yalnızca `VKN-001` geçerse çalışır) |
| `TCKN-001` | `header.alici_vkn_tckn` | `error` | Tam **11 ASCII rakam**, ilk hane `0` olamaz |
| `TCKN-002` | aynı | `error` | **TCKN checksum** — 10. ve 11. hane (yalnızca `TCKN-001` geçerse) |
| `ID-001` | `header.alici_vkn_tckn` | `error` | Uzunluk ne 10 ne 11 → ne VKN ne TCKN biçimi |
| `FNO-001` | `header.fatura_no` | `warning` | `^[A-Z]{3}[0-9]{13}$` (e-Fatura: 3 harf + 13 rakam) sapması |
| `KDV-001` | `kalemler[i].kdv_orani` | `warning` | Oran `{1, 10, 20}` kümesinde değil |
| `ARITH-001` | `header.{ara_toplam, kdv_toplam, genel_toplam}` | `error` | `ara_toplam + kdv_toplam == genel_toplam` |
| `ARITH-002` | `header.ara_toplam` + tüm `kalemler[i].satir_tutari` | `error` | `Σ(satir_tutari) == ara_toplam` |
| `ARITH-003` | `kalemler[i].{miktar, birim_fiyat, satir_tutari}` | `error` | `miktar × birim_fiyat == satir_tutari` |

### Kimlik numarası dispatch'i

`satici_vkn` her zaman VKN'dir (satıcı vergi mükellefidir): yalnızca `VKN-001`/`VKN-002` uygulanır.

`alici_vkn_tckn` hem 10 haneli VKN hem 11 haneli TCKN taşıyabilir (bkz. `docs/SCHEMA.md` §3), bu
yüzden **uzunluğa göre** dispatch edilir:

| Uzunluk | Uygulanan kurallar |
| ------- | ------------------ |
| 10 | `VKN-001`, `VKN-002` |
| 11 | `TCKN-001`, `TCKN-002` |
| diğer | `ID-001` |

> Uzunluk 10 olan fakat rakam içermeyen bir değer (`"ABCDEFGHIJ"`) VKN'ye dispatch edilir ve
> `VKN-001` biçim hatası verir — `ID-001` değil. Bu bilinçlidir: `ID-001` yalnızca **uzunluk**
> hiçbir kimlik türüne uymadığında kullanılır.

### Sayısal karşılaştırma politikası

- Tüm karşılaştırmalar **`Decimal`** ile **tam eşitliktir**; `float` kullanılmaz (D-017).
- **Tolerance veya yuvarlama kuralı v0.1'de tanımlanmamıştır** (`docs/EVALUATION.md` §4 ile
  hizalı). Sınırları için §6'ya bakınız.
- **Scale farkı bulgu üretmez:** `Decimal("20.00") == Decimal("20")` sayısal olarak doğrudur,
  dolayısıyla `3.000,00` ile `3000` aynı değerdir.
- KDV oranı **yüzde puanı** birimindedir (`%20` → `Decimal("20")`), `docs/SCHEMA.md` §5 ile aynı.

---

## 4. Rule ID ve sürümleme politikası

- **Rule ID formatı:** `<AILE>-<NNN>` — aile kuralın konusunu (`VKN`, `TCKN`, `ID`, `FNO`, `KDV`,
  `ARITH`), numara aile içindeki sırayı verir.
- **Rule ID'ler kalıcıdır.** Bir kural kaldırılırsa kimliği **yeniden kullanılmaz**; kaydedilmiş
  eski raporlar okunabilir kalır.
- **`ruleset_version`** kural kümesinin sürümüdür ve `Invoice.schema_version`'dan **bağımsızdır.**
  Kural eklenmesi/kaldırılması, bir kuralın anlamının veya severity'sinin değişmesi ya da
  `ALLOWED_KDV_RATES` kümesinin değişmesi bu sürümü artırır.
- Şema v0.1 **FROZEN**'dır (D-058). Freeze'de alan adları değişmediği için rule ID'ler ve
  `field_path` değerleri de değişmemiştir.

---

## 5. Authoritative kaynak referansları

| Konu | Kaynak |
| ---- | ------ |
| VKN (vergi kimlik numarası) checksum algoritması | Gelir İdaresi Başkanlığı (GİB) vergi kimlik numarası doğrulama algoritması |
| TCKN (T.C. kimlik numarası) checksum algoritması | Nüfus ve Vatandaşlık İşleri Genel Müdürlüğü (NVİ) T.C. kimlik numarası algoritması |
| KDV oranları (%1, %10, %20) | 3065 sayılı Katma Değer Vergisi Kanunu md. 28 ve 07.07.2023 tarihli Cumhurbaşkanı Kararı (oranların %8→%10 ve %18→%20 olarak güncellenmesi) |
| e-Fatura numara biçimi (3 harf + 13 rakam) | GİB e-Fatura UBL-TR kılavuzu — fatura numarası: 3 karakter seri kodu + 4 haneli yıl + 9 haneli sıra numarası |

> **Uyarı:** KDV oran kümesi **zamana bağlıdır.** Yukarıdaki küme, bu ruleset sürümünün yazıldığı
> tarihte yürürlükte olan oranları yansıtır ve `ruleset_version` ile birlikte donmuştur. Mevzuat
> değişirse kural değil, **ruleset sürümü** güncellenir. Ayrıca kural, faturanın **tarihine göre
> dönemsel oran** kontrolü yapmaz (bkz. §6).

---

## 6. Bilinen sınırlar

Bunlar eksiklik değil, **v0.1 için bilinçli kapsam kararlarıdır.** Her biri, gerçek fatura verisi
görülmeden çözülmesi doğru olmayan bir soruya karşılık gelir.

### İskonto (indirim) — desteklenmiyor

`LineItem` yalnızca beş alan taşır ve `iskonto` bunlardan biri değildir (D-018). Satır veya fatura
düzeyinde indirim içeren bir faturada `ARITH-002` ve `ARITH-003` **doğru extraction'da bile**
tutmaz. Kural bunu **iskonto olarak tanıyamaz**, yalnızca bir `error` üretir. v0.1 bu faturaları
insan denetimine yönlendirir.

### Tevkifat (vergi sorumlusu kesintisi) — desteklenmiyor

Tevkifatlı faturalarda ödenecek tutar, hesaplanan KDV'nin tamamını içermez. Şemada tevkifat alanı
bulunmadığından `ARITH-001` bu faturalarda **hatalı biçimde** `error` üretebilir.

### Çoklu vergi ve çok oranlı KDV — kısmen desteklenmiyor

- ÖTV, konaklama vergisi, damga vergisi gibi **ek vergiler** şemada yoktur; `ARITH-001`'i bozarlar.
- **Çok oranlı KDV** (aynı faturada %10 ve %20 satırlar) satır düzeyinde temsil edilebilir, fakat
  `kdv_toplam`'ın satır oranlarından **türetilebilirliği doğrulanmaz** — v0.1'de böyle bir kural
  yoktur (`ara_toplam × oran / 100` kontrolü kapsamda değildir).

### Yuvarlama toleransı yok

Karşılaştırmalar tam eşitliktir. Gerçek faturalarda `miktar × birim_fiyat` sonucu kuruşa
yuvarlanmış olabilir (ör. `3 × 33,333 = 99,999` fakat belgede `99,99` yazar). Böyle bir satır
`ARITH-003` **false positive** error üretir. Tolerance **bilinçli olarak uydurulmamıştır:**
`docs/EVALUATION.md` §4 ile hizalı biçimde, eşik ancak gerçek veriyle gerekçelendirilerek ayrı bir
karar olarak eklenecektir.

### Diğer sınırlar

- **Dönemsel oran kontrolü yok:** `KDV-001` fatura tarihine bakmaz; 2023 öncesi tarihli meşru bir
  %8/%18 faturası warning üretir. `%0` (istisna/muafiyet) de warning üretir — bu yüzden kural
  `error` değil `warning`'dir.
- **Kâğıt fatura numarası:** `FNO-001` e-Fatura kalıbını bekler. Serbest seri/sıra biçimli kâğıt
  faturalar warning üretir; bu bir hata değil, **format sapması** sinyalidir. Fatura numarası
  hiçbir koşulda hard fail üretmez.
- **Tarih kuralı yok:** `fatura_tarihi` üzerinde makullük kontrolü (gelecek tarih, çok eski tarih)
  v0.1'de bulunmaz.
- **Unvan kuralı yok:** `satici_unvan` ve `alici_unvan` serbest metindir; deterministik olarak
  doğrulanamaz (`docs/SCHEMA.md` §3 "Kritik: Hayır").
- **Satır sayısı kuralı yok:** kalem sayısının belgeyle uyumu bir **evaluation** sorusudur
  (`docs/EVALUATION.md` §5 Kademe 1), validation kuralı değil.
- **Mükerrer fatura tespiti yok:** tek belge, durumsuz (stateless) doğrulama; geçmiş faturalara
  bakılmaz.

---

## 7. Testler

`backend/tests/validation/` — FastAPI ve veritabanı olmadan, yalnızca sentetik veriyle çalışır.

| Dosya | Kapsam |
| ----- | ------ |
| `test_identifiers.py` | VKN/TCKN biçim ve checksum; uzunluk, karakter ve Unicode rakam hataları; algoritma dalları; ön koşul ihlali |
| `test_rules.py` | Her kuralın tek tek davranışı; KDV sınırları; Decimal scale farkı; `missing`/`unreadable` → not_evaluable ve reason önceliği |
| `test_validate_invoice.py` | Sabit sıra, tekrarsızlık, determinizm, boş/eksik kalem container'ı, confidence alanı bulunmaması, framework bağımsızlığı |

**Kimlik numarası test vektörleri sentetiktir:** gerçek bir belgeden alınmamış, checksum
algoritmasından **türetilmiştir** ve hiçbir kişi, kurum, isim veya adresle ilişkilendirilemez.
Sabit vektörlerin sessizce çürümesini engellemek için "geçerli kontrol hanesi tektir" özelliği de
ayrıca doğrulanır.

---

## İlgili belgeler

- Şema kontratı: [`SCHEMA.md`](SCHEMA.md) (`v0.1 FROZEN`)
- Evaluation metodolojisi: [`EVALUATION.md`](EVALUATION.md)
- Karar günlüğü: [`DECISIONS.md`](DECISIONS.md) (D-033…D-040 bu belgeyi kapsar)
- Ürün kapsamı: [`PROJECT_BRIEF.md`](../PROJECT_BRIEF.md) §5, §7
