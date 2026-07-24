# DocumentFlow AI — Uçtan Uca Akış ve Ürün Yüzeyi

```text
Workflow contract: v0.1
Review surface:    minimal FastAPI + server-rendered HTML
Provider:          SEÇİLMEDİ (recorded/demo ile sürülüyor)
Status:            DRAFT
```

Bu belge, PROJECT_BRIEF §3'teki MVP akışının uygulanmış hâlini tanımlar:
**yükle → çıkar → doğrula → yönlendir → düzelt → onayla → JSON export → audit**.
Katman **kod olarak uygulanmıştır** (`backend/src/documentflow/{workflow,db,api}/`).

> **Demo uyarısı.** Model kararı ertelendiği için (D-049) uygulama `recorded`
> extractor ile çalışır: yüklenen PDF ne olursa olsun aynı sentetik faturayı
> döndürür ve **gerçek çıkarım yapmaz**. Review ekranı bunu görünür bir banner ile
> bildirir; kullanıcıya gerçek çıkarım yapıldığı izlenimi verilmez.

---

## 1. Katmanlar

| Katman | Yer | Bilir |
| ------ | --- | ----- |
| Domain | `documentflow.schema` | Hiçbir şey (saf kontrat) |
| Çekirdek hesaplama | `parsing`, `validation`, `extraction`, `flagging`, `ingestion` | Domain |
| Akış | `documentflow.workflow` | Domain + çekirdek + **DB** |
| Kalıcılık | `documentflow.db` | SQLAlchemy |
| Ürün yüzeyi | `documentflow.api` | Hepsi + FastAPI |

`workflow` **FastAPI-agnostiktir**: `Session` ve `ExtractorProtocol` dışarıdan verilir, hiçbir
web framework'ü import edilmez. Akış bu yüzden HTTP olmadan da (test, ileride CLI veya
zamanlayıcı) aynı biçimde sürülebilir.

Çekirdek katmanlar veritabanını da bilmez — `backend/tests/test_layer_boundaries.py` bunu AST
taramasıyla kilitler ve çekirdek testler veritabanısız çalışmaya devam eder.

---

## 2. Veri modeli (dokuz tablo)

| Tablo | Rol |
| ----- | --- |
| `documents` | Yüklenen belgenin metadata'sı; baytlar dosya sisteminde (D-047) |
| `extraction_runs` | Çıkarım denemesi + sağlayıcı metadata'sı (model, prompt sürümü, latency, token, tahmini maliyet) |
| `extracted_invoices` | **Değişmez** çıkarım anlık görüntüsü (JSONB) |
| `validation_findings` | Ruleset 0.1 bulguları, rapor sırasıyla |
| `review_flags` | Deterministik yönlendirme sinyalleri, üretim sırasıyla |
| `user_corrections` | Alan düzeltmeleri — **önce** ve **sonra** değerleriyle |
| `approvals` | Onay + düzeltmeler uygulanmış **yeni** anlık görüntü |
| `export_records` | Dışa aktarım anı ve `payload_sha256` |
| `audit_events` | Append-only olay akışı |

Tek kullanıcı; **auth, rol ve çok kullanıcılı yapı yoktur.** Generic repository veya otomatik
CRUD katmanı da yoktur — sorgular ihtiyaç duyulan yerde açıkça yazılır.

### Neden `Invoice` JSONB olarak saklanıyor

Normalize edilmiş kolonlar `FieldValue` üçlüsü nedeniyle alan başına üç kolon demek olurdu ve
şema o dönemde DRAFT'tı (D-021; artık D-058 ile frozen) — her şema değişikliği bir migration gerektirirdi. Snapshot'ın amacı
**audit doğruluğudur**: çıkarımın o anki hâlini birebir korumak. Sorgulanabilirlik ihtiyacı
doğarsa JSONB üzerinde indeks eklenebilir.

### Decimal ve JSON serileştirme

Anlık görüntüler `Invoice.model_dump(mode="json")` ile üretilir: `Decimal` değerler **metin**
olarak serileşir, JSON sayısı (dolayısıyla `float`) hiç oluşmaz. Geri okurken `Invoice`
doğrulaması `Numeric` BeforeValidator'ından geçer ve float reddedilir (D-017). Ondalık basamak
sayısı da korunur (`"3600.00"` ≠ `"3600.0"`). Parasal tahmin kolonu `Numeric(18,6)`'dır.

---

## 3. Akış adımları ve kuralları

### 1) Yükleme

`inspect_pdf` V1.0 kapsam kapısıdır (PROJECT_BRIEF §4): metin katmanı olmayan, şifreli, bozuk
veya PDF olmayan içerik burada **görünür biçimde** reddedilir. **Reddedilen belge diske
yazılmaz** — kapsam dışı içerik biriktirilmez; yalnızca metadata ve ret nedeni kaydedilir.

Kabul edilen belge içerik adresli olarak saklanır (SHA-256, D-047).

### 2) Çıkarım

`ExtractorProtocol.extract`. Sağlayıcıya **dosya adı gönderilmez**; opak bir belge kimliği
kullanılır. Başarısızlıkta run kaydedilir, snapshot **oluşmaz**, audit'e `extraction_failed`
yazılır.

### 3-4) Doğrulama ve yönlendirme

`validate_invoice` bulguları ve `build_review_flags` sinyalleri sırasıyla kaydedilir.
Flag'ler **LLM confidence içermez** (D-048).

### 5) Review ekranı

Sunucuda render edilen HTML. **SPA yoktur.** Ekran, düzeltmeler uygulanmış **güncel** durumu ve
güncel sinyalleri gösterir; çıkarımın **orijinal** bulgu ve flag'leri audit için veritabanında
korunur. Jinja2 autoescape açıktır — fatura metni güvenilmeyen girdidir.

### 6) Düzeltme

Kullanıcının girdisi, çıkarım çıktısıyla **aynı parser'lardan** geçer
(`extraction.parse_field_value` → `parse_tr_number` / `parse_tr_date`). Parse edilemeyen değer
reddedilir (400); sessizce kabul edilmez.

- **Orijinal anlık görüntü değişmez.** Düzeltme ayrı bir satırdır.
- **Önce ve sonra** değerleri (`before_raw`, `before_value`, `before_status`, `after_value`,
  `after_status`) saklanır — düzeltme denetlenebilirdir.
- Belgenin ham metni korunur; alan hiç yoksa (`missing`) kullanıcının girdisi `raw` olarak
  kullanılır (FieldValue invariant'ı `ok` için `raw` zorunlu kılar).
- Onaydan sonra düzeltme reddedilir (409).

### 7) Onay

Düzeltmeler orijinal görüntünün **kopyası** üzerine uygulanır ve sonuç
`approvals.approved_payload`'a yazılır. Bir çıkarım en fazla bir kez onaylanır (UNIQUE).

Onay anında kalan `blocking` sinyal sayısı audit detayına yazılır: insan bunlara **rağmen**
onaylamayı seçmiş olabilir ve bu kayıt görünür kalır. v0.1'de blocking sinyal onayı engellemez —
karar insanındır; sistem yalnızca kaydeder.

### 8) Export

**Onaylanmamış veri dışa aktarılamaz.** Onay yoksa istek 409 döner, `export_rejected` audit'e
yazılır ve **hiçbir veri üretilmez**. Onaylıysa gövde deterministik biçimde serileştirilir
(`sort_keys`, sabit ayraçlar) ve hash'i `export_records.payload_sha256`'ya yazılır — dışa
aktarılan içeriğin sonradan değişmediği doğrulanabilir.

Export **`POST /runs/{id}/export`** ile tetiklenir, GET ile değil (D-057): bir `export_records`
satırı ve `export_created` audit olayı ürettiği için yan etkilidir. GET rotalarının tamamı
safe kalır — browser prefetch, tekrar tıklama veya otomatik link taraması kazara export
üretmemelidir. Review ekranında export bu yüzden bir link değil, küçük bir POST formudur.
Kullanıcının bilerek yaptığı iki ayrı POST iki ayrı export kaydı üretir; bu beklenen
davranıştır (aynı onaylı görüntüden üretildikleri için `payload_sha256` aynıdır).

### 9) Audit

Her adım append-only bir olay yazar. Olay türleri: `document_uploaded` · `document_rejected` ·
`extraction_started` · `extraction_completed` · `extraction_failed` · `validation_completed` ·
`flags_generated` · `correction_applied` · `approved` · `export_created` · `export_rejected`.

**Sıralama `id` (identity) iledir, `occurred_at` ile değil:** PostgreSQL'de `now()` işlem
başlangıç zamanıdır ve aynı işlemdeki olaylar aynı damgayı alır; zaman damgasına göre sıralama
belirsiz olurdu.

**Audit detayına ne yazılmaz:** belge içeriği, alan **değerleri** ve dosya adı. Detay yalnızca
ayrımlayıcı bilgi taşır (sayılar, durumlar, kural kimlikleri, alan yolları). Düzeltmelerin
önce/sonra değerleri `user_corrections` satırında zaten denetlenebilir durumdadır.

---

## 4. HTTP yüzeyi

| Route | İş |
| ----- | -- |
| `GET /` | Belge listesi + yükleme formu |
| `POST /documents` | PDF yükle → ingest → extract → validate → flag |
| `GET /runs/{id}` | Review ekranı |
| `POST /runs/{id}/corrections` | Alan düzeltme (400: parse edilemedi / bilinmeyen alan) |
| `POST /runs/{id}/approve` | Onay (409: zaten onaylı) |
| `POST /runs/{id}/export` | Onaylı JSON export (**409: onaylanmamış**) |
| `GET /runs/{id}/audit` | Olaylar sırasıyla |
| `GET /health` | Sağlık kontrolü |

Kapsam dışı (bilinçli): batch yükleme, kuyruk, worker, çok kullanıcı, auth, SPA.

---

## 5. Gizlilik

- Gerçek belgeler `data/private/` altında; `.gitignore` ile dışlı (D-029). Repoya girmez.
- Belge baytları veritabanına **yazılmaz** (D-047).
- Sağlayıcıya dosya adı gönderilmez.
- Audit detayı alan değeri ve dosya adı taşımaz.
- `error_detail` yalnızca alan yolu + hata kodu özetidir (D-045).
- Log mesajlarına belge içeriği yazılmaz.

---

## 6. Bilinen sınırlar

- **Gerçek çıkarım yok.** `recorded` sağlayıcı sabit bir yanıt döndürür; doğruluk, gecikme ve
  maliyet hakkında hiçbir ölçüm veya iddia yoktur.
- **Yeniden çıkarım (re-run) yüzeyi yok.** Aynı belge için ikinci bir çıkarım akış katmanında
  mümkündür fakat arayüzde tetiklenmez.
- **Düzeltme geri alma yok.** Yeni bir düzeltme eskisinin üzerine yazar; ikisi de kayıtlıdır.
- **Onay geri alınamaz.**
- **Kalem ekleme/silme yok.** Yalnızca mevcut alanlar düzeltilebilir.
- **Sayfalama yok** (liste son 50 belge ile sınırlı).
- **Eşzamanlılık varsayımı: tek kullanıcı.** Aynı çıkarım üzerinde paralel düzeltme senaryosu
  ele alınmamıştır.

---

## İlgili belgeler

- Extraction sözleşmesi: [`EXTRACTION.md`](EXTRACTION.md)
- Validation kuralları: [`VALIDATION.md`](VALIDATION.md)
- Flagging sözleşmesi: [`FLAGGING.md`](FLAGGING.md)
- Şema kontratı: [`SCHEMA.md`](SCHEMA.md)
- Karar günlüğü: [`DECISIONS.md`](DECISIONS.md) (D-050…D-057)
- Ürün kapsamı: [`PROJECT_BRIEF.md`](../PROJECT_BRIEF.md) §3, §5, §7, §9
