# DocumentFlow AI — Veri Toplama ve Schema Review İş Akışı

```text
Schema version: v0.1 — FROZEN (2026-07-23, D-058)
Status:         Aktif iş akışı belgesi
```

Bu belge, schema v0.1'in gerçek Türkçe faturalar üzerinde **temsil gücünü (schema
representability)** incelemek için gerçek belgelerin **Git dışında, lokal ve private**
biçimde nasıl toplanacağını, anonim envanterin nasıl tutulacağını ve schema coverage
review'un nasıl yapılacağını tanımlar.

> **Bu belge bir hukuki uygunluk garantisi değildir.** Yalnızca veri kaynağı, kullanım
> gerekçesi ve inceleme bağlamını kayıt altında tutan bir yöntem tanımıdır.

---

## 1. Amaç

- Gerçek faturalarla **schema representability** incelemesi yapmak.
- **Extraction accuracy ölçmek DEĞİL** (bunun için pipeline ve bağımsız ground truth
  gerekir; bkz. `docs/EVALUATION.md` §1 seviye C).
- Schema freeze kararını varsayıma değil, **gerçek belge yapılarına** dayandırmak.

Ground-truth etiketleme bu aşamada yapılmaz; schema coverage review, ground-truth
etiketleme değildir (bkz. `docs/EVALUATION.md` §11).

---

## 2. İki veri seti ayrımı

### 2.1 Freeze candidate set

Schema v0.1'in **kapsam içi** gerçek belgeler üzerinde temsil gücünü değerlendirmek
için kullanılır.

- ~~Hedef: **10–12 belge**~~ → **tarihsel hedef; D-058 ile supersede edildi.**
  Erişilebilir kapsam içi gerçek belge sayısı pratikte **3**'te kaldı ve freeze bu
  N=3 üzerinde, gözlenen representability temelinde verildi.
- **Gerçekleşen freeze seti: 3 belge** (`FZ-001`, `FZ-002`, `FZ-003`), 2026-07-23.
- Türkçe
- TRY
- Text-layer dijital PDF (bkz. §6)
- Ticari fatura
- Line item içeren
- Mümkün olduğunca **farklı görsel layout ailesi** — gerçekleşen sette bu çeşitlilik
  **sınırlıdır**: üçü de tek sayfalı, tek satırlı, tek KDV oranlı, tüketiciye kesilen
  e-Arşiv faturasıdır.
- Lokal/private saklanan

### 2.2 Challenge set

Mevcut **kapsam dışı veya karmaşık** yapıların gerçek belgelerde nasıl göründüğünü
anlamak için kullanılır. Örnek kategoriler:

- Tevkifatlı fatura
- Genel iskontolu fatura
- KDV dışında başka vergi/fon içeren belge
- Döviz veya uluslararası fatura

Challenge set:

- **Schema freeze başarısına dahil edilmez.**
- **Extraction accuracy hesabına dahil edilmez.**
- Yalnızca **kapsam kararlarını** (neyin bilinçli olarak dışarıda tutulduğunu)
  kanıtlamak için kullanılır.

**Gerçekleşen challenge seti: 4 belge** (2026-07-23), anonim kategorileriyle:

| ID | Kategori | v0.1 dışında kalma nedeni |
| -- | -------- | ------------------------- |
| `CH-001` | Çok sayfalı yapı | İki sayfalı belge; v0.1 tek sayfalı dar kapsamı hedefler |
| `CH-002` | İstisna / tevkifat / iskonto | İstisna-muafiyet-tevkifat terimleri, düşük veya sıfır KDV oranı ve iskonto birlikte görülüyor; v0.1'de bu vergi yapıları ve iskonto alanı yok |
| `CH-003` | Türkçe e-Arşiv düzeni dışı | Standart Türkçe başlık etiketleri (fatura no / fatura tarihi / VKN / KDV) bulunmuyor; yabancı sağlayıcı fatura yapısı |
| `CH-004` | Çok sayfalı yapı | İki sayfalı belge |

**Excluded set: 5 belge.** Bunlar ne freeze'e ne evaluation denominator'ına girer ve
ayrıntılı analiz edilmez; yalnızca kapsam dışı oldukları kayıt altındadır.

---

## 3. Anonim belge ID standardı

Freeze candidate belgeleri: `FZ-001`, `FZ-002`, …
Challenge belgeleri: `CH-001`, `CH-002`, …

Anonim belge ID:

- Gerçek fatura numarası **değildir**.
- Şirket adına göre **üretilmez**.
- Dosyanın kaynağını **açığa çıkarmaz**.
- Coverage ve raporlama belgelerinde **tek referans** olarak kullanılır.

Gerçek dosya adları yalnızca **lokal ve ignored** envanterde (`local_filename` kolonu)
tutulabilir. **Public dokümanlara gerçek dosya adı yazılmaz.**

---

## 4. Lokal (Git dışı) çalışma alanı

Aşağıdaki yapı yalnızca lokaldir ve `.gitignore` ile dışlanmıştır (`data/private/`):

```text
data/private/
├── freeze_candidates/
│   └── originals/          # gerçek freeze candidate PDF'leri (lokal, ignored)
├── challenge_set/
│   └── originals/          # gerçek challenge PDF'leri (lokal, ignored)
├── synthetic_examples/     # sentetik destek seti (bkz. §11)
│   ├── originals/
│   ├── inventory/
│   │   └── synthetic_inventory.csv
│   └── review/
├── inventory/
│   ├── freeze_inventory.csv
│   └── challenge_inventory.csv
└── review/
    ├── schema_coverage.csv
    └── line_item_coverage.csv
```

Gerçek belgeler yalnızca `originals/` altında lokal tutulur; **repoya asla eklenmez.**
Public repoda yalnızca boş şablonlar bulunur (`docs/templates/`).

---

## 5. Envanter ve coverage alan tanımları

Aşağıdaki tanımlar hem lokal CSV dosyaları hem de `docs/templates/` altındaki public
şablonlar için geçerlidir. Public şablonlar aynı kolon yapısını taşır ancak **veri
satırı içermez.**

### 5.1 Inventory alanları

- `anonymous_document_id`: `FZ-001` / `CH-001` biçiminde anonim ID.
- `local_filename`: gerçek dosya adı — **yalnızca lokal ignored dosyada** doldurulur.
- `challenge_category` (yalnızca challenge): tevkifat / iskonto / çoklu vergi / döviz vb.
- `source_category`: `personal_purchase`, `permitted_business_source`, `self_issued`
  veya başka **anonim** kategori.
- `usage_basis`: `self_document` veya `explicit_permission`.
- `document_type`: belge türünün anonim tanımı (ör. `commercial_invoice`).
- `layout_family`: görsel olarak benzer şablonları gruplamak için anonim değer
  (ör. `LAYOUT-01`). Gerçek şirket adı değildir.
- `integrator_if_visible`: e-fatura entegratörü belgede **açıkça görünüyorsa** yazılır;
  **tahmin edilmez.**
- `text_layer_present`, `line_items_present`, `discount_present`,
  `withholding_present`, `multiple_tax_types_present`: boolean → `yes` / `no` /
  `unknown`.
- `language`, `currency`: ör. `tr`, `TRY`.
- `collection_date`: toplama tarihi (ISO-8601).
- `notes`: **gerçek şirket, kişi, VKN, TCKN, adres, fatura numarası veya tutar
  içermez.**

### 5.2 `schema_coverage.csv` alanları

- `present_in_document`: `yes` / `no`.
- `human_readable`: `yes` / `no` / `not_applicable`.
- `observed_format_category`: **gerçek değeri değil**, format kategorisini tutar
  (ör. "GG.AA.YYYY", "boşluklu binlik", "yüzde işaretli").
- `representable_by_current_type`: `yes` / `no` / `uncertain`.
- `parser_support_status`: `supported` / `unsupported_returns_unreadable` /
  `silent_misparse_risk` / `not_applicable` / `not_tested`.
- `schema_gap_category`: `none` / `missing_field` / `insufficient_type` /
  `ambiguous_semantics` / `parser_gap` / `scope_excluded`.
- `scope_classification`: `in_scope` / `challenge` / `out_of_scope`.

> Gerçek alan **değerleri** bu dosyaya yazılmaz; yalnızca kategoriler.

### 5.3 `line_item_coverage.csv` alanları

- `line_items_present`, `five_fields_available`, `multiline_description_present`,
  `discount_present`, `multiple_vat_rates_present`, `additional_tax_present`,
  `model_supports_planned_arithmetic`: boolean → `yes` / `no` / `unknown`.
- `row_structure_category`: satır yapısının anonim kategorisi.
- `schema_gap_category`, `scope_classification`: §5.2 ile aynı değer kümeleri.

---

## 6. Çeşitlilik yaklaşımı

- **Farklı şirket sayısı tek başına layout çeşitliliğini garanti etmez.** Farklı
  şirketler aynı entegratör şablonunu kullanabilir.
- **Entegratör bilgisi** faydalı bir metadata olabilir ancak tek belirleyici değildir.
- **Görsel layout ailesi ayrıca kaydedilmelidir** (`layout_family`).
- Aynı veya çok benzer layout tekrarları örneklem çeşitliliğini **yapay biçimde
  artırmamalıdır.**

---

## 7. Gizlilik

- İnceleme **orijinal belgeler üzerinde ve lokalde** yapılır.
- Dışarı (public repoya) çıkan **yalnızca anonim coverage matrisidir.**
- **Orijinal belge anonimleştirilerek incelenmez;** anonimleştirme format ve aritmetik
  yapıyı bozabilir ve schema representability incelemesini geçersiz kılabilir.
- Gerçek VKN/TCKN, unvan, adres, fatura numarası ve tutarlar **public repoya yazılmaz.**
- **Kendi faturaları da** üçüncü taraf kişisel veya ticari veri içerebilir.
- **Veri sahipliği, gizlilik yükümlülüklerini ortadan kaldırmaz.**
- İzinli işletme belgeleri (`permitted_business_source`) yalnızca **açık izinle**
  kullanılmalıdır.
- Bu doküman bir **hukuki uygunluk garantisi değildir.**

### 7.1 Görsel redaksiyon güvenli DEĞİLDİR

**Bir PDF'in üzerine siyah kutu çizmek veya metni görsel olarak kapatmak, text layer'ı
silmez.** Belge görsel olarak redakte edilmiş görünür fakat gerçek değerler metin
katmanında aynen durmaya devam eder ve herhangi bir metin çıkarıcı tarafından okunabilir.

Bu, bu depoda **gözlenmiş bir durumdur**: görsel olarak redakte edilmiş bir kopyanın
metin katmanı, redakte edilmemiş orijinaliyle **byte-identical** çıkmıştır (aynı
SHA-256). Yani redaksiyon hiçbir bilgi kaldırmamıştı.

Bu nedenle:

- Görsel olarak redakte edilmiş belgeler **güvenli anonim kopya sayılmaz** ve öyle
  kullanılmaz.
- Bu tür dosyalar `excluded/unsafe_redaction/` altında, **lokal ve ignored** tutulur;
  freeze veya evaluation setine **girmez**.
- Bir belgenin gerçekten anonim olduğu, görsel görünümüne değil **çıkarılmış metnine**
  bakılarak doğrulanır.

---

## 8. V1 kapsam ayrımı

- **V1.0 (mevcut MVP):** yalnızca **text-layer dijital PDF.**
- **V1.1:** taranmış PDF ve görseller (PNG/JPEG), OCR/vision tabanlı ingestion.
- **V1.2:** telefon fotoğrafı, eğri/gölgeli/bulanık düşük kaliteli belgeler.

**Taranmış veya fotoğraf belgeler freeze candidate setine alınmaz.** Freeze candidate
set yalnızca V1.0 kapsamındaki text-layer dijital PDF'lerden oluşur (bkz.
`PROJECT_BRIEF.md` §4).

---

## 9. Schema freeze kriterleri (referans)

Freeze kriterleri **extraction accuracy'ye bağlı değildir** ve `docs/EVALUATION.md`
§8'de tanımlıdır. Burada tekrarlanmaz; dört kriter:

1. Temsil edilebilirlik
2. Çözülmemiş boşluk olmaması
3. Format kapsamı
4. LineItem yeterliliği

> Coverage matrisi bu kriterleri ölçmek için kullanılan **yöntemdir;** ayrı bir freeze
> kriteri değildir.

**Durum:** şema 2026-07-23'te **frozen**'dır (D-058). Dört kriter, erişilebilir 3 kapsam
içi gerçek belge üzerinde sağlandı. Başlangıçtaki 10–12 belgelik sayı hedefi
uygulanabilir olmadığı için D-058 ile supersede edildi. Freeze bir **accuracy kanıtı
değildir** ve N=3 dış geçerlilik sağlamaz.

---

## 10. Dosya iş akışı

1. Belge lokal `originals/` klasörüne konur (freeze veya challenge).
2. Anonim ID atanır (`FZ-###` / `CH-###`).
3. Lokal inventory doldurulur (`local_filename` yalnızca burada).
4. İnsan **orijinal belgeyi** inceler.
5. Lokal coverage matrisleri **gerçek değer yazılmadan** (yalnızca kategoriler)
   doldurulur.
6. Yalnızca **anonim kategoriler ve toplamlar** public rapora aktarılır.
7. Elde edilen bulgularla schema **freeze veya revizyon** kararı verilir
   (ayrı bir commit ile; bkz. `docs/EVALUATION.md` §8).

---

## 11. Sentetik destek seti

Gerçek belge setlerinden (§2) **ayrı** tutulan, lokal ve ignored bir yardımcı settir.
Amacı, gerçek belge toplama süreci beklenmeden parser ve şema geliştirmesini
ilerletebilmektir.

### 11.1 Amaç ve sınırlar

- Sentetik örnekler gerçek freeze belgelerinin **yerine geçmez.**
- **Schema freeze sayısına dahil edilmez** (freeze kriterleri: `docs/EVALUATION.md` §8).
- **Extraction accuracy** (`docs/EVALUATION.md` §1 seviye C) veya **processing
  reliability** (§1 seviye D) metriklerine **dahil edilmez.**
- Kullanım alanı yalnızca şunlardır:
  - **Parser format coverage** (`docs/EVALUATION.md` §1 seviye B),
  - **Schema gap keşfi,**
  - **Özel durum (edge case) geliştirmesi,**
  - **Regresyon testi tasarımı.**
- Gerçek ve sentetik sonuçlar **hiçbir raporda tek tabloda birleştirilmez;** ayrı
  bölüm ve ayrı tablo olarak sunulur.
- Her sentetik örneğin **kaynağı (`source_method`) ve senaryosu (`scenario_name`)
  envanterde açıkça kaydedilir.**
- **Aynı GİB/XSLT layout'undan üretilen farklı senaryolar layout çeşitliliği
  sayılmaz** (§6 ile tutarlı; bu örnekler aynı `layout_family` değerini taşır).
- Sentetik içerikte **gerçek ad, adres, VKN/TCKN, e-posta, telefon veya gerçek şirket
  verisi kullanılmaz** (§7 ile tutarlı).

### 11.2 Lokal klasör yapısı ve ID

Sentetik örnekler yalnızca lokalde, `data/private/synthetic_examples/` altında tutulur
ve `.gitignore` ile dışlanmıştır (bkz. §4). Public repoda yalnızca boş şablon bulunur
(`docs/templates/synthetic_inventory_template.csv`).

Anonim ID biçimi: `SY-001`, `SY-002`, … Freeze (`FZ-`) ve challenge (`CH-`)
serilerinden **ayrı bir seridir** ve onlarla birlikte sayılmaz.

### 11.3 Envanter alanları ve değer kümeleri

`synthetic_inventory.csv` alanları (§5.1'den farklı olanlar):

- `scenario_name`: senaryonun kısa ve anonim adı (bkz. §11.4).
- `source_method`: `gib_test_portal` / `official_ubl_example` / `locally_generated`.
- `discount_level`: `none` / `invoice` / `line` / `both`.
- `intended_test_purpose`: örneğin hangi geliştirme veya test amacı için üretildiği
  (ör. `parser_format_coverage`, `regression_fixture`).
- `generation_date`: üretim tarihi (ISO-8601).
- `included_in_schema_freeze`: **her zaman `false`.**
- `included_in_accuracy_metrics`: **her zaman `false`.**
- `text_layer_present`, `line_items_present`, `multiple_vat_rates_present`,
  `vat_exemption_present`, `withholding_present`, `additional_tax_present`:
  boolean → `yes` / `no` / `unknown` (§5.1 ile aynı değer kümesi).
- `document_type`, `layout_family`, `language`, `currency`: §5.1 ile aynı anlamda.
- `notes`: **gerçek şirket, kişi, VKN, TCKN, adres, fatura numarası veya tutar
  içermez.**

Bu envanterde `local_filename` kolonu **yoktur;** sentetik dosyalar gerçek belge
değildir ve gizlenmesi gereken bir kaynak dosya adı taşımaz.

### 11.4 İlk hedef senaryolar

| Senaryo | `scenario_name` |
| --- | --- |
| Standart tek satırlı satış faturası | `standard_single_line` |
| Çok satırlı standart fatura | `standard_multi_line` |
| Birden fazla KDV oranı | `multiple_vat_rates` |
| Fatura seviyesinde iskonto | `invoice_level_discount` |
| Satır seviyesinde iskonto | `line_level_discount` |
| KDV istisnalı veya muafiyetli fatura | `vat_exemption` |

> Bunlar yalnızca **başlangıç senaryolarıdır;** liste kapalı değildir. Parser veya
> şema geliştirmesi sırasında yeni senaryolar eklenebilir.

---

## İlgili belgeler

- Evaluation metodolojisi: [`EVALUATION.md`](EVALUATION.md) (freeze kriterleri §8)
- Şema kontratı: [`SCHEMA.md`](SCHEMA.md) (`v0.1 FROZEN`)
- Ürün kapsamı (V1.0/V1.1/V1.2): [`../PROJECT_BRIEF.md`](../PROJECT_BRIEF.md) §4
- Public şablonlar: [`templates/`](templates/)
