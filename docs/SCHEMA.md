# DocumentFlow AI — Extraction Şeması

```text
Schema version: v0.1
Status: DRAFT — NOT FROZEN
```

Bu belge, faturadan çıkarılan yapılandırılmış verinin v0.1 şemasını (Pydantic modelleri ve
Türkçe parser'lar) insan-okunur biçimde tanımlar. Şema **kod olarak uygulanmıştır**
(`backend/src/documentflow/schema/` ve `backend/src/documentflow/parsing.py`); bu belge o
uygulamayı birebir açıklar.

## Durum ve sınırlar (ÖNEMLİ)

- Şema **henüz gerçek Türkçe fatura örnekleriyle doğrulanmamıştır.**
- **Ground-truth (referans) etiketleme BAŞLAMAMALIDIR.** Şema donmadan etiketlenen veri, şema
  değişirse çöpe gider.
- **Ham fatura toplama BAŞLAYABİLİR** (etiketleme olmadan). Toplanan belgeler yalnızca yerelde
  tutulur.
- **Gerçek faturalar public repoya EKLENMEZ.** Hassas belge ve dataset klasörleri `.gitignore`
  ile dışlanmıştır.
- **Freeze (dondurma) kararı, ilerideki bir şema review adımında** gerçek örneklerle doğrulama
  sonrası verilecektir. Bu belge bir freeze kaydı değildir.

---

## 1. FieldValue kontratı

Çıkarılan her alan, ham metni ve parse edilmiş değeri tek bir sarmalayıcıda (`FieldValue[T]`)
birlikte taşır. Bu, çıkarımın izlenebilir ve denetlenebilir olmasını sağlar.

| Alan | Tip | Anlam |
| ---- | --- | ----- |
| `raw` | `str \| None` | Belgede görülen ham metin. `None` ya da whitespace-strip sonrası boş olmayan bir metin. |
| `value` | `T \| None` | Parse edilmiş, normalize edilmiş değer (ör. `Decimal`, `date`, `str`, `list[LineItem]`). |
| `status` | `FieldStatus` | Alanın çıkarım durumu: `ok`, `missing` veya `unreadable`. |

### Whitespace normalizasyonu

`raw` alanına verilen değer boş string (`""`) veya yalnızca boşluk içeriyorsa **`None`'a
indirgenir**. Böylece "hiç değer yok" (None), "boş string" ve "boşluk" arasında ayrım kalmaz;
üçü de değerin yokluğu (→ `missing`) olarak ele alınır.

### Yapısal invariant'lar (status'a göre)

Bunlar **yapısal bütünlük** kurallarıdır; iş (business) kuralı değildir. Pydantic
`model_validator` ile zorlanır ve ihlalde nesne hiç oluşmaz.

| `status` | `raw` | `value` |
| -------- | ----- | ------- |
| `ok` | boş olmayan metin (zorunlu) | non-None `T` (zorunlu) |
| `unreadable` | boş olmayan metin (zorunlu) | `None` |
| `missing` | `None` | `None` |

Ek kural: `value` non-None **ancak ve ancak** `status == ok` olduğunda.

- **`ok`**: Alan belgede vardı ve başarıyla parse edildi. Hem `raw` hem `value` doludur.
- **`missing`**: Beklenen alan belgede **hiç yoktu**. `raw` ve `value` ikisi de `None`.
- **`unreadable`**: Alan belgede **vardı ama güvenilir biçimde parse edilemedi** (bozuk/anlamsız
  metin). `raw` doludur, `value` `None`'dur. (Not: v0.1 yalnızca metin-katmanlı dijital PDF'i
  hedeflediğinden, "bölge var ama sıfır karakter" gibi OCR'a özgü durumlar kapsam dışıdır; bu
  yüzden `unreadable` her zaman ham metin taşır.)

### Yapısal invariant vs business validation

- **Yapısal invariant** (bu şema): `raw`/`value`/`status` üçlüsünün tutarlılığı. Örn. `ok` iken
  `value` boş olamaz. Modelin var olabilmesi için gereken kurallar.
- **Business validation** (bu şemada YOK): Alanlar arası matematik ve mantık. Örn.
  `satir_tutari == miktar * birim_fiyat`, `genel_toplam == ara_toplam + kdv_toplam`, VKN
  checksum, tarih makullüğü. Bunlar deterministik doğrulama katmanına aittir; şema/parser
  katmanında **bulunmaz**. Uygulanan kural kümesi için bkz. [`VALIDATION.md`](VALIDATION.md)
  (ruleset 0.1).

---

## 2. Model hiyerarşisi

```text
Invoice
├── schema_version: str = "0.1"          # metadata (FieldValue DEĞİL)
├── header: InvoiceHeader                # 9 alan, her biri FieldValue
└── kalemler: FieldValue[list[LineItem]] # container: raw=tablo metni, status, value=satırlar
```

`schema_version` çıkarılan bir alan değildir; kontrat sürümünü taşıyan sabit metadatadır.
Belge kimliği, dosya adı, zaman damgası, maliyet/latency gibi **processing metadata modelde
bulunmaz** (bunlar ileride ingestion/persistence katmanına aittir).

---

## 3. Header alanları (9 alan)

Her alan `FieldValue[...]` sarmalayıcısıyla modelde **her zaman bulunur**; belgede yoksa
`status=missing` ile temsil edilir. "Kritik" işareti, ilgili alanın validation'a girmesinin
beklendiğini gösterir. Fiilen kural uygulanan alanların kesin listesi için bkz.
[`VALIDATION.md`](VALIDATION.md) §3 kural kataloğu.

> Alan adları kanonik kontrat adlarıdır. Özellikle `alici_vkn_tckn`, alanın hem 10 haneli VKN
> hem 11 haneli TCKN taşıyabildiğini yansıtır (bkz. §6).

### `fatura_no`
- **Tanım:** Fatura numarası / seri-sıra no.
- **Parse tipi:** `str` (serbest metin, normalize edilmez).
- **Belgede beklenen:** Evet. **Kritik:** Evet (kimlik).
- **Sentetik raw:** `"ABC2025000000123"` → **Normalize:** `"ABC2025000000123"`.
- **Bilinen varyasyonlar:** e-Fatura 16 haneli (3 harf + 13 rakam) vs kağıt fatura serbest
  seri/sıra biçimleri; ayrım v0.1'de garanti edilmez (bkz. §6).
- **Missing/Unreadable:** Belgede yoksa `missing`; okunamıyorsa (bozuk) `unreadable`.

### `fatura_tarihi`
- **Tanım:** Fatura düzenlenme tarihi.
- **Parse tipi:** `date` (bkz. `parse_tr_date`).
- **Belgede beklenen:** Evet. **Kritik:** Evet.
- **Sentetik raw:** `"15.03.2025"` → **Normalize:** `date(2025, 3, 15)`.
- **Bilinen varyasyonlar:** Ayraç `.`/`/`/`-`. ISO, metinsel ay ("15 Mart 2025") ve 2 haneli
  yıl v0.1 kapsamı dışıdır.
- **Missing/Unreadable:** Tarih yoksa `missing`; parse edilemeyen tarih (ör. `31.13.2025`) alanı
  `unreadable` yapar (parser `None` döner, extraction katmanı durumu atar).

### `satici_unvan`
- **Tanım:** Satıcı (tedarikçi) unvanı / ticari adı.
- **Parse tipi:** `str`.
- **Belgede beklenen:** Evet. **Kritik:** Hayır (serbest metin; deterministik doğrulaması zor).
- **Sentetik raw:** `"ACME Bilişim Ltd. Şti."` → **Normalize:** `"ACME Bilişim Ltd. Şti."`.
- **Bilinen varyasyonlar:** Çok satırlı unvan, kısaltmalar (Ltd. Şti., A.Ş.).
- **Missing/Unreadable:** Yoksa `missing`; okunamıyorsa `unreadable`.

### `satici_vkn`
- **Tanım:** Satıcı vergi kimlik numarası (VKN, 10 hane).
- **Parse tipi:** `str` (rakam dizisi; sayısal işlem yapılmaz, başındaki sıfırlar korunur).
- **Belgede beklenen:** Evet. **Kritik:** Evet (VKN checksum ile doğrulanabilir — Aşama 3).
- **Sentetik raw:** `"1234567890"` → **Normalize:** `"1234567890"`.
- **Bilinen varyasyonlar:** "VKN:", "Vergi No" etiketleriyle; boşluk/ayraç içerebilir.
- **Missing/Unreadable:** Yoksa `missing`; okunamıyorsa `unreadable`.

### `alici_unvan`
- **Tanım:** Alıcı (müşteri) unvanı veya adı-soyadı.
- **Parse tipi:** `str`.
- **Belgede beklenen:** Evet. **Kritik:** Hayır.
- **Sentetik raw:** `"Beta Ticaret A.Ş."` → **Normalize:** `"Beta Ticaret A.Ş."`.
- **Bilinen varyasyonlar:** Bireysel alıcıda ad-soyad; kurumsal alıcıda unvan.
- **Missing/Unreadable:** Yoksa `missing`; okunamıyorsa `unreadable`.

### `alici_vkn_tckn`
- **Tanım:** Alıcı vergi/kimlik numarası. Alıcı işletme ise **VKN (10 hane)**, birey ise
  **TCKN (11 hane)** olabilir. Alan adı bu ikiliği kanonik olarak yansıtır.
- **Parse tipi:** `str` (rakam dizisi).
- **Belgede beklenen:** Genelde evet (bireysel bazı fişimsi belgelerde eksik olabilir).
  **Kritik:** Evet (checksum ile doğrulanabilir — Aşama 3).
- **Sentetik raw:** `"0987654321"` → **Normalize:** `"0987654321"`.
- **Bilinen varyasyonlar:** VKN (10) vs TCKN (11) uzunluk farkı.
- **Missing/Unreadable:** Yoksa `missing`; okunamıyorsa `unreadable`.

### `ara_toplam`
- **Tanım:** Mal/hizmet ara toplamı (KDV hariç matrah).
- **Parse tipi:** `Decimal` (bkz. `parse_tr_number`).
- **Belgede beklenen:** Evet. **Kritik:** Evet (matematik: `ara_toplam + kdv_toplam == genel_toplam`).
- **Sentetik raw:** `"3.000,00"` → **Normalize:** `Decimal("3000.00")`.
- **Bilinen varyasyonlar:** "Mal/Hizmet Toplam Tutarı", "Ara Toplam" etiketleri; `TL`/`₺` ekli.
- **Missing/Unreadable:** Yoksa `missing`; parse edilemeyen tutar `unreadable`.

### `kdv_toplam`
- **Tanım:** Toplam KDV tutarı (tüm oranların toplamı).
- **Parse tipi:** `Decimal`.
- **Belgede beklenen:** Evet. **Kritik:** Evet (matematik).
- **Sentetik raw:** `"600,00"` → **Normalize:** `Decimal("600.00")`.
- **Bilinen varyasyonlar:** "Hesaplanan KDV", "KDV Toplam" etiketleri; birden çok orana ait
  KDV satırları toplanmış olabilir.
- **Missing/Unreadable:** Yoksa `missing`; okunamıyorsa `unreadable`.

### `genel_toplam`
- **Tanım:** Ödenecek genel toplam (KDV dahil).
- **Parse tipi:** `Decimal`.
- **Belgede beklenen:** Evet. **Kritik:** Evet (matematik).
- **Sentetik raw:** `"3.600,00 TL"` → **Normalize:** `Decimal("3600.00")`.
- **Bilinen varyasyonlar:** "Ödenecek Tutar", "Genel Toplam" etiketleri; `TL`/`₺` ekli.
- **Missing/Unreadable:** Yoksa `missing`; okunamıyorsa `unreadable`.

---

## 4. Line item (kalemler) yapısı

- **Container:** `kalemler: FieldValue[list[LineItem]]`. Aynı `FieldValue` mekanizması kullanılır:
  - `status`: `ok` (tablo parse edildi), `missing` (kalem yok) veya `unreadable` (tablo bölgesi
    var ama satırlara ayrıştırılamadı).
  - `raw`: **tüm kalem tablosunun ham metni** (audit/izlenebilirlik kaynağı).
  - `value`: `list[LineItem]`.
- **Satır bazlı ayrı ham metin tutulmaz.** Bir satırın "hamlığı" beş hücresinin `FieldValue.raw`
  değerlerinde dağıtık durur. LineItem'a ekstra `raw`/`status` alanı eklenmez (K5 gereği zaten
  yalnızca beş alan vardır).
- **LineItem alt alanları da `FieldValue` kullanır.**

### LineItem — tam beş alan (K5)

| Alan | Parse tipi | Sentetik raw → Normalize |
| ---- | ---------- | ------------------------ |
| `aciklama` | `str` | `"Danışmanlık Hizmeti"` → `"Danışmanlık Hizmeti"` |
| `miktar` | `Decimal` | `"2"` → `Decimal("2")` |
| `birim_fiyat` | `Decimal` | `"1.500,00"` → `Decimal("1500.00")` |
| `kdv_orani` | `Decimal` (yüzde puanı) | `"%20"` → `Decimal("20")` |
| `satir_tutari` | `Decimal` | `"3.000,00"` → `Decimal("3000.00")` |

### v0.1 dışı (bilinçli olarak yok)

- `birim` (ölçü birimi: adet/kg/saat)
- `iskonto` (satır indirimi)
- satır bazlı KDV tutarı (yalnızca `kdv_orani` var, tutar türetilmez)
- ilave ürün/satır metadata alanları (GTIP, stok kodu vb.)

---

## 5. Numeric ve parser davranışı

- **Float kullanılmaz.** Tüm sayısal/parasal değerler `Decimal`'dır. `Decimal(float)` ikili
  yuvarlama hatasını kalıcı kıldığından, sayısal alanlara **float girişi reddedilir**
  (`str`/`int`/`Decimal` kabul edilir). Bkz. §6 float notu.
- **Normalize sayısal değer `Decimal`'dır.** Türkçe biçim (`.` binlik, `,` ondalık) `Decimal`'a
  çevrilir: `"1.234,56"` → `Decimal("1234.56")`.
- **KDV oranı yüzde puanı biçimindedir:** `"%20"` → `Decimal("20")` (yani `20`, `0.20` değil).
  İlgili KDV tutarı hesabı (Aşama 3) `matrah * oran / 100` biçiminde yapılır.
- **Parser'lar durum (`FieldStatus`) üretmez.** Saf fonksiyondurlar; `raw` metnini yapısal olarak
  parse eder. Ham metni `FieldValue` durumuna çevirmek extraction katmanının işidir.
- **Parse başarısızlığında mevcut kontrata göre `None` döner** (istisna fırlatılmaz;
  parse edilememe normal bir sonuçtur).
- **Desteklenen formatlar yalnızca testlerle doğrulanmış olanlardır** (gerçek faturadan önce
  kapsam bilinçli olarak dar tutulmuştur):

**`parse_tr_number` — desteklenen (testli):**
`1.234,56` · `1.234,56 TL` · `1.234,56 TRY` · `₺1.234,56` · `%20` · `20%` · `-1.234,56` ·
`1 234,56` (boşluk) · NBSP'li · `0` · `1.234.567,89`.
**None döner (testli):** `""`, yalnızca boşluk, `abc`, `1,2,3`, `--5`, `None`.
**Kapsam dışı (ertelendi):** parantezli negatif `(1.234,56)`, ISO/Anglo ondalık, para birimi
kelimesi, ön ek para birimi.

**`parse_tr_date` — desteklenen (testli):**
`15.03.2025` · `15/03/2025` · `15-03-2025` (4 haneli yıl, ayraç `.`/`/`/`-`).
**None döner (testli):** `31.13.2025` (geçersiz ay), `32.01.2025`, `5.3.2025` (tek hane),
`2025-03-15` (ISO), `15.03-2025` (karışık ayraç), `15.03.25` (2 haneli yıl), `abc`, `""`, `None`.

---

## 6. Bilinen sınırlamalar

- **Belge türü alanı yoktur** (v0.1'de fatura tipi: satış/iade vb. modellenmez).
- **Kağıt vs e-Fatura numara formatı** kesin olarak ayrılamaz; `fatura_no` serbest `str`'dir.
- **Validation kuralları ayrı bir katmandadır** ([`VALIDATION.md`](VALIDATION.md), ruleset 0.1);
  bu şema/parser katmanında hiçbir business kural yoktur.
- **İskontolu veya karmaşık satır yapıları** v0.1 kapsamını aşabilir (yalnızca beş LineItem alanı).
- **Şema henüz gerçek faturalarla doğrulanmamıştır** (DRAFT).
- **Float "bypass" durumu (çözüldü — bilinen teknik not):** Domain modellerinde float sızıntısı
  **yoktur**. Bir `FieldValue[Numeric]` alanına float verildiğinde Pydantic (typed constructor,
  dict/JSON ve önceden yapılmış bir bare instance'ın modele enjekte edildiği yollar dahil) onu
  yeniden doğrular ve **reddeder**. Yalnızca (a) hiçbir modele konmamış **standalone bare**
  `FieldValue(value=2.0)` (inert; hiçbir faturaya bağlı değil) ve (b) `model_construct(...)`
  (tüm validasyonu bilinçli atlayan escape hatch) float tutabilir. Bu davranış regresyon
  testleriyle kilitlenmiştir (`tests/test_field_value.py`), böylece ileride sessizce regres
  edemez. Mutlak "hiçbir FieldValue float tutamaz" garantisi istenirse ileride `FieldValue`
  seviyesinde küçük bir kontrol eklenebilir; v0.1'de pratik risk sıfır olduğu için eklenmemiştir.
- **Alan adlandırma (kanonik):** Header alan adları kanonik kontratla hizalanmıştır:
  `alici_vkn_tckn` (alan hem 10 haneli VKN hem 11 haneli TCKN taşıyabildiğinden veri kapsamını
  tam ifade eder) ve `kdv_toplam`. Şema draft olduğu ve dış tüketici bulunmadığı için bu,
  alias/deprecated alan olmadan doğrudan rename ile uygulanmıştır.

---

## 7. Freeze öncesi yapılabilecekler / yapılamayacaklar

| Yapılabilir | Yapılamaz (freeze'e kadar) |
| ----------- | -------------------------- |
| Ham fatura toplama (yerel) | Ground-truth etiketleme |
| Şema/parser üzerinde iterasyon | Şemayı "frozen/locked" ilan etmek |
| Sentetik örneklerle test | Gerçek faturaları repoya eklemek |
| Bu belgeyi güncellemek | Business validation kurallarını şemaya koymak |

Freeze, gerçek örneklerle doğrulama yapan ayrı bir **şema review** adımında kararlaştırılacaktır.
