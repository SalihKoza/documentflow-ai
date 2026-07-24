# DocumentFlow AI — Extraction Sözleşmesi

```text
Extraction contract: v0.1
Schema version:      v0.1 (FROZEN — 2026-07-23, D-058)
Provider:            SEÇİLMEDİ (karar ertelendi)
Status:              DRAFT
```

Bu belge, bir faturadan yapılandırılmış veri çıkarma katmanının **sağlayıcıdan bağımsız
sözleşmesini** tanımlar. Katman **kod olarak uygulanmıştır**
(`backend/src/documentflow/extraction/`, `ingestion/`, `documents/`); bu belge o uygulamayı
birebir açıklar.

> **Gerçek bir LLM sağlayıcısı henüz bağlanmamıştır.** Model ve sağlayıcı seçimi bilinçli olarak
> ertelendi (bkz. §8). Bu, sözleşmenin bir eksikliği değil sınavıdır: aşağıdaki her şey —
> dönüşüm, hata taksonomisi, testler — hiçbir sağlayıcı olmadan çalışır ve test edilir.

---

## 1. Kapsam ve sınır

| Bu katman **yapar** | Bu katman **yapmaz** |
| ------------------- | -------------------- |
| Belgeyi V1.0 kapsamı için kabul/ret eder (`ingestion`) | OCR veya görüntü işleme |
| Ham belgeyi içerik adresli olarak saklar (`documents`) | Belge içeriğini yorumlamak |
| Sağlayıcı yanıtını domain `Invoice`'ına çevirir (`extraction`) | İş kuralı doğrulaması (bkz. [`VALIDATION.md`](VALIDATION.md)) |
| Sağlayıcı hatalarını kontrollü domain sonuçlarına çevirir | İstisna fırlatarak çağıranı sürprize uğratmak |
| Cost ve latency ölçüm noktalarını taşımak | Faturalandırma gerçeğini iddia etmek |

Çekirdek paketler **saf**tır: `fastapi`, `sqlalchemy`, `psycopg`, `anthropic`, `openai` gibi
hiçbir transport/DB/sağlayıcı importu içermezler. Bu bir stil tercihi değil, D-004'ün
uygulanmasıdır ve `backend/tests/test_layer_boundaries.py` içinde AST taramasıyla kilitlenmiştir.

---

## 2. Sözleşme

### Giriş noktası

```python
class ExtractorProtocol(Protocol):
    def extract(self, request: ExtractionRequest) -> ExtractionResult: ...
```

`typing.Protocol` bilinçli olarak ABC yerine kullanılır: adapter'lar bir taban sınıftan **türemek
zorunda değildir**, yalnızca imzayı karşılamaları yeterlidir. Bu, sağlayıcı paketlerinin domain'e
bağımlı olmasını önler.

### `ExtractionRequest`

| Alan | Tip | Anlam |
| ---- | --- | ----- |
| `document_id` | `str` | **Anonim/opak** belge kimliği — gerçek dosya adı değildir (`DATA_COLLECTION.md` §3). |
| `content` | `bytes` | Ham belge. `repr=False` ile işaretlidir: kazara log'a veya `repr`'e düşmez. |
| `media_type` | `str` | Varsayılan `application/pdf`. |
| `page_count` | `int \| None` | Ingestion'ın gözlediği sayfa sayısı. |

Sağlayıcı ayarı (model adı, API anahtarı, timeout) **bu modelde yoktur**; o, adapter'ın kendi
yapılandırmasıdır.

### `ProviderMetadata`

Çıkarımı **kimin, neyle ve ne maliyetle** ürettiği. `Invoice`'tan **ayrıdır** — domain modeli
yalnızca belgeden çıkarılan veriyi taşır, çalışma bilgisi buraya yazılır. Sağlayıcı değiştiğinde
domain kontratı değişmez.

`provider` · `model` · `prompt_version` · `schema_version` · `latency_ms` · `input_tokens` ·
`output_tokens` · `cache_read_input_tokens` · `cache_creation_input_tokens` ·
`estimated_cost_usd` (**`Decimal`**, float değil) · `request_id`

**Confidence/olasılık alanı yoktur** ve eklenmeyecektir (PROJECT_BRIEF §5).

### `ExtractionResult`

| Alan | Anlam |
| ---- | ----- |
| `status` | `ExtractionStatus` (§4). |
| `invoice` | Domain `Invoice`. **non-None ancak ve ancak `status == ok`** — `model_validator` ile zorlanır. |
| `metadata` | `ProviderMetadata`. |
| `parse_failures` | Sağlayıcı `ok` dediği hâlde değeri parse edilemeyen alan yolları (§5). |
| `error_detail` | Kısa teşhis metni. **Belge içeriği asla buraya yazılmaz** (§6). |

Bu invariant, `FieldValue`'nun (D-015/D-016) yapısal invariant desenini sonuç düzeyinde
tekrarlar: başarısız bir çıkarım "yarım" bir `Invoice` döndürmez.

---

## 3. Wire DTO — sağlayıcının üretmesi gereken JSON

`backend/src/documentflow/extraction/wire.py`. Domain modelinin dışa dönük karşılığıdır ve
ondan **ayrı tutulur**. İki neden:

### 3.1 Sayısal alanlar **metindir** (float tuzağı, D-017)

JSON sayıları Python'da `float` olur ve şemadaki `Numeric` BeforeValidator'ı float'ı reddeder.
Bu yüzden wire DTO'sunda **tüm sayısal alanlar `str`'dir**:

```json
{ "raw": "3.600,00 TL", "value": "3.600,00", "status": "ok" }
```

Metin → `Decimal`/`date` çevrimi mevcut **`parsing.py` → `parse_tr_number` / `parse_tr_date`**
ile yapılır; yeni bir sayı ayrıştırıcı yazılmaz. Sağlayıcıya "sayıyı metin olarak döndür" demek,
tüm zinciri float'tan uzak tutmanın en basit yoludur.

### 3.2 `extra="forbid"` — fazladan alan sessizce yutulmaz

Sağlayıcı sözleşmede olmayan bir alan döndürürse (en önemlisi **`confidence`**) sonuç
`schema_mismatch` olur. Bu, PROJECT_BRIEF §5'in kod düzeyindeki ikinci savunma katmanıdır:
metadata'da confidence alanı olmaması yetmez, gelen bir confidence'ın **fark edilmesi** de
gerekir.

`status` için domain enum'u (`FieldStatus`) yeniden kullanılır; tanımsız bir durum değeri
reddedilir.

---

## 4. Hata taksonomisi

Sağlayıcı istisnaları **dışarı sızmaz**; adapter onları aşağıdaki değerlere çevirir.
`status != ok` olan her sonuçta `invoice is None`.

| `ExtractionStatus` | Ne zaman |
| ------------------ | -------- |
| `ok` | Yanıt sözleşmeye uydu ve `Invoice`'a çevrildi |
| `invalid_json` | Yanıt geçerli JSON değil |
| `schema_mismatch` | JSON geçerli fakat sözleşmeye uymuyor: eksik/fazla alan, geçersiz `status`, yanlış `schema_version`, yapısal invariant ihlali, **`confidence` gibi beklenmeyen alan** |
| `provider_error` | Rate limit, sunucu hatası, bağlantı hatası |
| `timeout` | İstek zaman aşımına uğradı |
| `refused` | Sağlayıcı isteği reddetti |
| `truncated` | Çıktı token sınırı nedeniyle yarım kaldı |

Gerçek adapter eklendiğinde yalnızca **eşleme** yazılacaktır (SDK istisnası → yukarıdaki değer);
dönüşüm ve doğrulama yolu değişmez.

---

## 5. "Tahmin yok" kuralı — `parse_failures`

Sağlayıcı bir alan için `ok` dediği hâlde değer parse edilemiyorsa, mapping katmanı **değeri
tahmin etmez**: alanı `unreadable`'a düşürür (raw korunur, value `None`) ve alan yolunu
`parse_failures`'a yazar.

Bu, `docs/EVALUATION.md` §1 seviye B'deki **"sessiz yanlış parse kabul edilmez"** kuralının
uygulamasıdır. Ayrım flagging katmanında korunur: `parse_failure` sinyali "model okuduğunu
söyledi ama değer çevrilemedi" demektir ve `field_unreadable`'dan farklı bir inceleme davranışı
gerektirir (bkz. [`FLAGGING.md`](FLAGGING.md)).

Aynı kural boş/yalnızca boşluk içeren metin değerleri için de geçerlidir.

---

## 6. Gizlilik: hata metni belge içeriği taşımaz

Pydantic doğrulama hataları varsayılan olarak **girdi değerlerini** içerir — yani belge içeriğini.
Bu yüzden `error_detail`, hataların yalnızca **alan yolu (`loc`) + kararlı hata kodu (`type`)**
özetinden üretilir; `msg` ve `input` alanları bilinçli olarak dışarıda bırakılır.

```text
header.ekstra_alan: extra_forbidden; header.fatura_no.confidence: extra_forbidden
```

Bir regresyon testi (`test_error_detail_does_not_leak_document_values`) bunu kilitler.
`ExtractionRequest.content` de `repr=False` taşır: belge baytları kazara log'a düşmez.

---

## 7. Cost ve latency ölçüm noktaları

Ölçüm **adapter'ın sorumluluğudur** ve `ProviderMetadata`'ya yazılır:

| Ölçüm | Nerede doldurulur |
| ----- | ----------------- |
| `latency_ms` | Adapter, sağlayıcı çağrısını **monotonic saatle** sarmalar (duvar saati değil) |
| `input_tokens` / `output_tokens` | Sağlayıcının bildirdiği kullanım değerleri |
| `cache_read_input_tokens` / `cache_creation_input_tokens` | Prompt cache etkisini ayrı görebilmek için |
| `estimated_cost_usd` | Model kimliğine bağlı **`Decimal`** fiyat tablosundan hesaplanır |

> **`estimated_cost_usd` bir tahmindir, fatura gerçeği değildir.** Liste fiyatından hesaplanır;
> indirim, batch fiyatlandırması ve cache repricing hesaba katılmaz. Ham token sayıları her zaman
> yanında raporlanır (D-030'un aynı ruhu: türetilmiş sayı, ham sayı olmadan sunulmaz).

`prompt_version` ve `model` alanları da metadata'da taşınır: ölçüm hangi prompt ve model
sürümüyle alındığı bilinmeden anlamsızdır.

---

## 8. Sağlayıcı ve model neden seçilmedi

Model kararı bilinçli olarak ertelendi. Bunun mümkün olması sözleşmenin doğru kurulduğunun
kanıtıdır: bu katmanın **hiçbir parçası** hangi modelin seçileceğine bağlı değildir.

Gerçek adapter eklendiğinde yapılacaklar sınırlıdır:

1. `providers/<saglayici>_extractor.py` — `ExtractorProtocol`'u karşılayan tek modül; SDK importu
   yalnızca burada bulunur.
2. SDK istisnası → `ExtractionStatus` eşlemesi (§4).
3. `build_result` çağrısı — dönüşüm ve doğrulama yolu **yeniden yazılmaz**.
4. Model adı, API anahtarı ve timeout `core/config.py` üzerinden; anahtar koda yazılmaz,
   loglanmaz, hata metnine konmaz.
5. Gerçek API testleri normal test suite'ine **zorunlu olmaz**.

---

## 9. Ingestion (V1.0) ve belge saklama

### `inspect_pdf` — kapsam kapısı

V1.0 yalnızca **metin katmanlı dijital PDF**'i destekler (PROJECT_BRIEF §4). Kapsam dışı belge
zincirin başında ve **görünür** biçimde reddedilir; sağlayıcıya hiç gönderilmez. Böylece
"çıkarım kötü çalıştı" ile "belge kapsam dışı" karışmaz.

Kontrol sırası ucuzdan pahalıya: `%PDF-` imzası → boyut → ayrıştırma → şifreleme → metin katmanı.

| `PdfRejectionReason` | Anlam |
| -------------------- | ----- |
| `not_pdf` | PDF imzası yok |
| `too_large` | Boyut sınırını aşıyor (varsayılan 20 MB) |
| `encrypted` | Şifreli belge |
| `no_text_layer` | Çıkarılabilir metin eşiğin altında (taranmış belge → V1.1) |
| `unreadable` | Ayrıştırılamayan/bozuk gövde |

Reddedilse bile gözlenen özellikler (`page_count`, `text_character_count`) raporlanır — teşhis
için gereklidir.

### Ham PDF saklama — dosya sistemi + metadata/path

**Karar:** PDF baytları dosya sisteminde tutulur; veritabanı yalnızca metadata ve **göreli yol**
saklar (PostgreSQL `bytea` değil).

Gerekçe: gerçek faturalar zaten `data/private/` altında ve `.gitignore` ile dışlı (D-029) — aynı
yerde durmaları gizlilik politikasıyla doğal olarak hizalanır; belge baytları veritabanı
yedeklerine ve dökümlerine girmez. Tek kullanıcı/tek belge ölçeğinde `bytea`'nın sunduğu tek
gerçek avantaj (transactional atomiklik) karşılığında ödenen bedel (yedek büyümesi, hassas
içeriğin dökümlere sızması) orantısızdır.

Yol **içerik adreslidir** (SHA-256): aynı belge iki kez yüklendiğinde tek dosya kalır ve yol
tamamen onaltılık karakterlerden türediği için dışarıdan gelen bir ad dizin ağacında gezinemez.
Yazım atomiktir (geçici dosya + `os.replace`); yarım yazılmış dosya hiçbir zaman görünmez.
Saklama kökü **otomatik oluşturulmaz** — yapılandırmadaki bir yazım hatası belgeleri beklenmedik
bir yere dağıtmamalıdır.

> **Veritabanı satırı ve migration bu aşamada üretilmemiştir.** Onu tüketecek bir persistence
> veya API katmanı henüz yok; tüketicisi olmayan tablo D-012 ile çelişir. Karar `DECISIONS.md`'de
> kayıtlıdır ve DB tarafı persistence/API fazında bu karara göre eklenecektir.

---

## 10. Bilinen sınırlar

- **Gerçek sağlayıcı yok.** Uçtan uca doğruluk, gecikme ve maliyet hakkında hiçbir ölçüm veya
  iddia yoktur.
- **Gerçek belge yok.** Repo'da hiç fatura PDF'i bulunmadığından zincir yalnızca **sentetik**
  PDF ve kaydedilmiş yanıtlarla sürülmüştür. Bu bir external validity kanıtı değildir
  (`docs/EVALUATION.md` §1).
- **Prompt yazılmamıştır.** `prompt_version` alanı taşınır, fakat henüz bir prompt yoktur.
- **Metin katmanı eşiği sezgiseldir.** Varsayılan 32 karakter; gerçek belge dağılımıyla
  ayarlanmalıdır.
- **Çok sayfalı/çok belgeli akış yoktur** (MVP tek belge, PROJECT_BRIEF §7).
- **Şema FROZEN'dır** (D-058): freeze'de alan adları değişmediği için `parse_failures` içindeki
  alan yolları da sabittir.

---

## 11. Testler

`backend/tests/{extraction,ingestion,documents}/` — API anahtarı, ağ ve veritabanı olmadan.

| Dosya | Kapsam |
| ----- | ------ |
| `extraction/test_mapping.py` | Geçerli payload; Decimal/date çevrimi; JSON sayısının reddi; geçersiz JSON; fazla alan ve `confidence`; `schema_version` uyumsuzluğu; missing/unreadable taşınması; parse düşürme ve yol sırası; hata metninde değer sızmaması |
| `extraction/test_adapters.py` | Protokol uyumu (mirassız); her başarısızlık durumu; `ExtractionResult` invariant'ları; `repr` gizliliği |
| `extraction/test_pipeline.py` | Uçtan uca: ingestion → recorded extraction → validation → flagging; determinizm |
| `ingestion/test_pdf.py` | Beş ret nedeni, eşik ayarı, invariant, determinizm |
| `documents/test_storage.py` | İçerik adresli yol, idempotenlik, atomik yazım, containment |
| `test_layer_boundaries.py` | Çekirdek katmanlarda framework/sağlayıcı importu bulunmaması (AST) |

**PDF fixture'ları kodda üretilir** (`tests/ingestion/_pdf_builder.py`): ikili test dosyası
repoya girmez, ne üretildiği görünür ve gözden geçirilebilir kalır.

---

## İlgili belgeler

- Şema kontratı: [`SCHEMA.md`](SCHEMA.md)
- Validation kuralları: [`VALIDATION.md`](VALIDATION.md)
- Flagging sözleşmesi: [`FLAGGING.md`](FLAGGING.md)
- Evaluation metodolojisi: [`EVALUATION.md`](EVALUATION.md)
- Karar günlüğü: [`DECISIONS.md`](DECISIONS.md) (D-041…D-049)
- Ürün kapsamı: [`PROJECT_BRIEF.md`](../PROJECT_BRIEF.md) §3, §4, §5
