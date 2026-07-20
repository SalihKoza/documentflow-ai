# DocumentFlow AI — Extraction Evaluation Metodolojisi

```text
Status: DRAFT
Schema version: v0.1
```

Bu belge, extraction (veri çıkarma) çıktısının **nasıl ölçüleceğini**, schema freeze
(şema dondurma) kriterlerini ve public repo veri gizliliği politikasını tanımlar. Bu bir
metodoloji sözleşmesidir; **ölçülmüş sonuç raporu değildir.**

## ⚠️ Önemli uyarı — buradaki sayılar sonuç değildir

- **Bu belgedeki hiçbir metrik henüz uygulanmış veya ölçülmüş bir sonuç değildir.**
  Örnekler yalnızca biçimi göstermek içindir.
- **Yüzdeler bir production performans iddiası değildir.** Yön gösterici hedefler (§10)
  bile üretim seviyesi garanti değildir.
- **Küçük seed set sonuçları yalnızca yön göstericidir** (directional); genellenemez.
- **Her yüzde, ham sayılarla (pay/payda) birlikte raporlanır.** Örnek:

  ```text
  85.4% (76/89)
  ```

  Yalnızca yüzde raporlamak (`85.4%`) **kabul edilmez.** Küçük örneklemde birkaç field
  instance sonucu ciddi biçimde değiştirebileceğinden ham sayılar zorunludur.

### Neden bu ayrımlar önemli (metodolojik çekirdek)

- **Mevcut testler implementation correctness gösterir.** `backend/tests/` altındaki
  sentetik testler, kodun tasarlandığı gibi davrandığını kanıtlar.
- **Gerçek faturalarla yapılacak çalışma external validity ve schema representability
  gösterir.** Bu ayrı bir sorudur: şema ve parser'lar gerçek dünyayı temsil ediyor mu?
- **Sentetik parser testleri, gerçek fatura format kapsamını kanıtlamaz.** Testlerin
  geçmesi, gözlenmemiş gerçek formatların desteklendiği anlamına gelmez.
- **Şema freeze kriterleri extraction performansına bağlı değildir** (bkz. §7).
- **Extraction accuracy ancak pipeline ve bağımsız ground truth mevcut olduğunda
  ölçülür** (bkz. §6/§7 seviye C).

---

## 1. Dört evaluation seviyesi (birleştirilmez)

Evaluation dört ayrı seviyede tanımlanır. **Bu seviyeler tek bir "overall accuracy"
metriği altında birleştirilmez;** her biri farklı bir soruyu yanıtlar ve farklı ön
koşullara sahiptir.

### A. Schema representability review

- **Soru:** Şema, gerçek belgelerdeki bilgiyi kayıpsız temsil edebiliyor mu?
- **Yöntem:** İnsan doğrudan orijinal belgeye bakar ve her kritik bilginin mevcut bir
  alanda, mevcut bir veri tipiyle saklanabildiğini işaretler.
- **Ön koşul:** **Extraction pipeline GEREKTİRMEZ.** Model çıktısı kullanılmaz.
- **Çıktı:** §8'deki coverage matrisi.

### B. Parser format coverage

- **Soru:** Gerçek belgelerde gözlenen sayı ve tarih formatları nasıl ele alınıyor?
- Her gözlenen format için üç olası sonuç:
  1. **Doğru parse ediliyor** (beklenen `Decimal`/`date` üretiliyor).
  2. **Bilinçli olarak desteklenmiyor** → alan `unreadable` durumuna düşüyor (parser
     `None` döndürüyor, extraction katmanı durumu atıyor).
  3. **Sessizce yanlış parse ediliyor** → **kabul edilmez;** bu bir hatadır ve
     düzeltilmesi gerekir.
- **Ön koşul:** Gözlenmiş gerçek formatların bir listesi (pipeline şart değildir; parser
  fonksiyonları izole çalıştırılabilir).

### C. Extraction accuracy

- **Soru:** Model, alan değerlerini ve durumlarını ne kadar doğru çıkarıyor?
- **Ön koşul:** Extraction **pipeline üretildikten** ve **bağımsız ground truth**
  (§6) hazırlandıktan sonra ölçülür. Bu belge yazıldığında bu ön koşullar **henüz
  sağlanmamıştır.**
- **Yöntem:** §3–§6.

### D. Processing reliability

- **Soru:** Pipeline bir belgeyi ne kadar güvenilir işliyor?
- **Metrikler:** valid structured output rate, processing failure rate, latency, cost
  (bkz. §12).
- **Ön koşul:** Çalışan extraction/ingestion pipeline.

---

## 2. Header field evaluation

Değerlendirilen dokuz kanonik header alanı:

`fatura_no` · `fatura_tarihi` · `satici_unvan` · `satici_vkn` · `alici_unvan` ·
`alici_vkn_tckn` · `ara_toplam` · `kdv_toplam` · `genel_toplam`

Header ve LineItem sonuçları **ayrı tablolarda** raporlanır (§6). Tek bir birleşik
accuracy metriği üretilmez.

### 2.1 Value accuracy

**Payda:** Ground truth'ta **hem mevcut hem insan tarafından okunabilir** field instance
sayısı.

```text
Value accuracy = Doğru değer / (GT'de mevcut ve okunabilir field instance sayısı)
```

Yalnızca ground truth'ta gerçekten var olan ve okunabilir alanlar paydaya girer. Belgede
hiç olmayan (`missing`) veya gerçekten okunamayan (`unreadable`) alanlar value accuracy
paydasına **dahil edilmez**; bunların değerlendirmesi status accuracy'e (§2.3) aittir.

Bir tahminin **doğru** sayılması için:

- Tahmin edilen `status` değeri **`ok`** olmalı, **ve**
- Normalize edilmiş `value`, ground truth normalize değeriyle **eşleşmeli**
  (metin için §3, sayısal için §5 kuralları).

**`raw` birebir eşleşmesi primary value accuracy'nin zorunlu parçası değildir.** `raw`
farkı ayrı bir tanısal metrik olarak (§2.2) raporlanır.

### 2.2 Raw fidelity (ayrı tanısal metrik)

`raw` değerin belge üzerindeki metni ne kadar iyi koruduğu **ayrı** raporlanır. Value
accuracy'den ayrı tutulmasının nedeni: doğru normalize değer üreten bir extraction,
önemsiz metin farkları yüzünden **tamamen yanlış** sayılmamalıdır. Bu farkların tipik
kaynakları:

- PDF text extraction whitespace farklılıkları
- Satır sonları (`\n`, `\r\n`)
- Unicode decomposition (NFC/NFD)
- Görsel olarak aynı fakat byte düzeyinde farklı karakterler

Örnek: `raw="1.234,56 TL"` ile `raw="1.234,56 TL"` (NBSP) value düzeyinde aynı
`Decimal("1234.56")` üretir; value accuracy açısından **doğru**, raw fidelity açısından
**farklı** raporlanır.

### 2.3 Status accuracy

**Payda:** Şemadaki **bütün etiketlenmiş field slotları** (belgede olmayanlar dahil,
dokuz header alanının tamamı her belge için).

```text
Status accuracy = Doğru status / (Tüm etiketlenmiş field slot sayısı)
```

Her slot için ground-truth status ile model status karşılaştırılır: `ok`, `missing`,
`unreadable`. **Status accuracy, value accuracy'den ayrı raporlanır** (paydaları
farklıdır ve farklı soruları yanıtlarlar).

### 2.4 Status hata kategorileri

Aşağıdaki kategoriler ayrı ayrı sayılır. **Yanlış değer üretme, alanı atlama ve
`unreadable` deme aynı hata sınıfında raporlanmaz** — bunlar davranışsal olarak farklı
hatalardır ve farklı düzeltmeler gerektirir.

| Ground truth                       | Tahmin              | Kategori                            |
| ---------------------------------- | ------------------- | ----------------------------------- |
| Alan var ve okunabilir             | `ok`, doğru değer   | Doğru çıkarım                       |
| Alan var ve okunabilir             | `ok`, yanlış değer  | Yanlış değer                        |
| Alan var ve okunabilir             | `missing`           | Kaçırılan alan                      |
| Alan var ve okunabilir             | `unreadable`        | Gereksiz abstention                 |
| Alan yok                           | `missing`           | Doğru yokluk                        |
| Alan yok                           | `ok`                | False positive / hallucinated alan  |
| Alan yok                           | `unreadable`        | Yanlış varlık algısı                |
| Alan var ama gerçekten okunamıyor  | `unreadable`        | Doğru unreadable                    |
| Alan var ama gerçekten okunamıyor  | `ok`                | Güvensiz değer üretimi              |

### 2.5 Ek status metrikleri (yalnızca tanım — hesaplama kodu yok)

Aşağıdaki oranlar ayrı raporlanabilir. Bu belgede formül hesaplayan kod yazılmaz;
yalnızca payda ve anlam tanımlanır.

| Metrik | Payda | Anlam |
| ------ | ----- | ----- |
| **Correct-missing rate** | GT'de gerçekten yok olan slotlar | Bu slotlarda modelin doğru biçimde `missing` demesi. |
| **False-positive rate** | GT'de gerçekten yok olan slotlar | Bu slotlarda modelin `ok` (halüsinasyon) veya değer üretmesi. |
| **Unreadable detection rate** | GT'de gerçekten okunamayan slotlar | Bu slotlarda modelin doğru biçimde `unreadable` demesi. |
| **Missed-field rate** | GT'de mevcut ve okunabilir slotlar | Bu slotlarda modelin yanlışlıkla `missing` demesi. |
| **Wrong-value rate** | GT'de mevcut ve okunabilir slotlar | Bu slotlarda modelin `ok` deyip yanlış değer üretmesi. |

---

## 3. Metin alanı karşılaştırma politikası

Metin alanlarında (`fatura_no`, `satici_unvan`, `alici_unvan`, `satici_vkn`,
`alici_vkn_tckn`, `aciklama`) **yalnızca tam string eşleşmesi yetersizdir.** Aynı bilgi,
byte düzeyinde farklı biçimlerde görünebilir.

### Birincil normalize karşılaştırma politikası

Karşılaştırmadan önce hem tahmin hem ground truth değerine **sırasıyla** şu işlemler
uygulanır:

1. **Unicode normalizasyonu** — NFC/NFD kaynaklı birleşik karakter (combining) farkları
   giderilir; görsel olarak aynı ama farklı kodlanmış karakterler eşitlenir.
2. **Türkçe büyük/küçük harf dönüşümü** — Türkçe diline özgü kurallarla (aşağıya bkz.).
3. **Baştaki ve sondaki whitespace'in kaldırılması** (trim).
4. **Tekrarlanan whitespace'in teke indirilmesi** (iç boşluklar tek boşluğa).

### Türkçe case dönüşümü (kritik)

Naif `.lower()` veya yalnızca `.casefold()` kullanımı **yeterli değildir.** Bunlar
Türkçe noktalı/noktasız `i` ayrımını bozar. Türkçe kurallara göre eşleme gereklidir:

```text
İ → i     (U+0130 noktalı büyük I  → noktalı küçük i)
I → ı     (U+0049 noktasız büyük I → noktasız küçük ı)
```

Ayrıca Unicode normalizasyonunda **NFD/NFC kaynaklı birleşik karakter (combining dot,
U+0307) farklılıkları** dikkate alınmalıdır; örneğin `İ` tek kod noktası (U+0130) ya da
`I` + combining dot biçiminde görünebilir ve ikisi eşitlenmelidir.

### Test edilmesi planlanan sentetik örnekler

Aşağıdaki değerler, ilgili varyantlarının normalize karşılaştırmada eşleşmesini (veya
uygun biçimde ayrışmasını) doğrulamak için kullanılacaktır:

- `IŞIK` ↔ `Işık`
- `İSTANBUL` ↔ `İstanbul`
- `ĞÜŞİÖÇ` (Türkçe'ye özgü harfler)
- combining-dot / NFD varyantları
- fazla whitespace (`"  ACME   Ltd  "`)
- satır sonu farklılıkları (`"ACME\nLtd"` ↔ `"ACME Ltd"`)

### Bu aşamada normalleştirilmeyecekler

Şimdilik otomatik olarak kaldırılmaz veya eşitlenmez (bilinçli karar):

- Noktalama işaretleri
- `A.Ş.` ↔ `AŞ`
- `Ltd. Şti.` ↔ `Ltd Şti`
- Kelime sırası
- Ticari unvan parçaları (kısaltma/genişletme)

**Gerekçe:** Bu tür alan-spesifik normalizasyonlar, gerçek veride düzenli varyasyon
gözlenmeden eklenirse yanlış eşleşme (false match) riski taşır. Gerçek veride düzenli
varyasyon görülürse, alan-spesifik normalizasyon daha sonra **gerekçeli bir karar
olarak** eklenebilir.

> **Kapsam notu:** Bu belge yalnızca karşılaştırma **kontratını** tanımlar.
> `normalize_for_comparison()` fonksiyonu bu görevde **yazılmaz;** ileride
> `documentflow/evaluation/` altında uygulanacaktır.

---

## 4. Numeric accuracy

Sayısal extraction alanları:

- **Header:** `ara_toplam`, `kdv_toplam`, `genel_toplam`
- **LineItem:** `miktar`, `birim_fiyat`, `kdv_orani`, `satir_tutari`

**Karşılaştırma kuralları:**

- Karşılaştırma **`Decimal`** ile yapılır; **float'a dönüştürme yapılmaz** (float,
  ikili yuvarlama hatası sokar; §schema D-017).
- **Exact normalized value karşılaştırması** kullanılır.
- **Bu aşamada tolerance veya rounding kuralı belirlenmez.** (İleride gerçek veriyle
  gerekçelendirilirse ayrı karar olarak eklenebilir.)
- **Arithmetic validation** (ör. `ara_toplam + kdv_toplam == genel_toplam`,
  `satir_tutari == miktar * birim_fiyat`) bu evaluation'ın parçası **değildir;**
  Aşama 3 validation katmanına aittir.

**Header numeric accuracy paydası:**

```text
Ground truth'ta mevcut ve okunabilir numeric header field instance sayısı
```

LineItem numeric alanları ayrı raporlanır ve §6'daki üç kademeli line-item kurallarına
tabidir (pozisyonel karşılaştırma yalnızca satır sayısı eşleştiğinde yapılır).

---

## 5. LineItem evaluation — üç kademe

LineItem sonuçları header'dan **ayrı tablolarda** raporlanır. Üç kademe, giderek daha
katı bir karşılaştırma sağlar ve bir üst kademe yalnızca ön koşulu sağlanınca uygulanır.

### Kademe 1 — Satır sayısı doğruluğu

Belge başına boolean:

```text
Tahmin edilen LineItem sayısı == Ground-truth LineItem sayısı
```

**Rapor:**

- Doğru satır sayısına sahip belge sayısı
- Toplam değerlendirilen belge sayısı
- Oran ve ham sayı — örn. `10/12 (83.3%)`

> Çok satırlı bir açıklamanın **yeni bir satır mı** yoksa **mevcut satırın devamı mı**
> olduğu, bir **annotation guide** içinde tanımlanır. Bu görevde annotation guide
> oluşturulmaz.

### Kademe 2 — Aritmetik tutarlılık

Extraction çıktısının kendi içinde, belge başına boolean:

```text
Σ(satir_tutari)  ile  ara_toplam  tutarlı mı?
```

**Kurallar:**

- Satır hizalaması (alignment) gerekmez.
- Satır sırası önemli değildir.
- `Decimal` kullanılır.
- Tolerance bu aşamada belirlenmez.

**Uyarılar (bu metrik tek başına extraction doğruluğunu kanıtlamaz):**

- Yanlış değerler tesadüfen tutarlı olabilir (ör. iki hata birbirini götürebilir).
- İskonto ve ek ücret içeren belgeler, doğru extraction'da bile uyumsuzluk yaratabilir.
- Gerçek validation kuralı Aşama 3'te yazılacaktır; bu yalnızca yön gösterici bir
  tutarlılık sinyalidir.

### Kademe 3 — Pozisyonel alan doğruluğu

**Yalnızca Kademe 1 başarılıysa** (satır sayısı eşleşiyorsa) uygulanır. Karşılaştırılan
beş alan, satır sırasına göre eşlenerek:

- `aciklama` (§3 metin kuralları) · `miktar` · `birim_fiyat` · `kdv_orani` ·
  `satir_tutari` (§4 numeric kuralları)

**Satır sayısı uyuşmazsa:**

- Kademe 1 raporlanır.
- Kademe 2 mümkünse raporlanır.
- **Kademe 3 atlanır.**
- **Zorla hizalama (forced alignment) yapılmaz.**

Semantic veya fuzzy alignment v0.1 kapsamı **dışındadır.**

---

## 6. Raporlama biçimi (header ve LineItem ayrı)

Header ve LineItem sonuçları **ayrı tablolarda** sunulur. **Tek bir overall accuracy
metriği oluşturulmaz.** Her hücrede yüzde, ham sayılarla birlikte verilir.

**Header (örnek biçim — sayılar temsilîdir, ölçülmüş değildir):**

| Alan | Value accuracy | Status accuracy | Raw fidelity |
| ---- | -------------- | --------------- | ------------ |
| `fatura_no` | — (n/N) | — (n/N) | — (n/N) |
| `ara_toplam` | — (n/N) | — (n/N) | — (n/N) |
| … | | | |

**LineItem (örnek biçim):**

| Kademe | Metrik | Sonuç |
| ------ | ------ | ----- |
| K1 | Satır sayısı doğru belge oranı | — (docs/docs) |
| K2 | Aritmetik tutarlı belge oranı | — (docs/docs) |
| K3 | Pozisyonel alan doğruluğu (yalnızca K1=✓) | — (n/N) |

---

## 7. Ground-truth bağımsızlığı

> **Kural:** Ground-truth etiketleri yalnızca orijinal belge incelenerek hazırlanır.
> İlk etiketleme sırasında extraction veya model çıktısı annotator'a gösterilmez.

**Önerilen süreç:**

1. Annotator yalnızca orijinal belgeyi görür.
2. Ground truth hazırlanır.
3. Etiket sürümü kilitlenir.
4. Extraction daha sonra çalıştırılır.
5. Tahmin ile ground truth karşılaştırılır.
6. Model çıktısı yalnızca hata analizi veya kontrollü adjudication sırasında açılır.

Tek kişilik projede bağımsızlık, **zaman ve erişim ayrımı** ile korunur: etiketleme,
extraction çıktısı üretilmeden ve görülmeden önce tamamlanır ve kilitlenir. İkinci bir
reviewer bu aşamada zorunlu değildir.

### Ground-truth gizliliği

- Gerçek belge ve label dosyaları **public repoya girmez.**
- Lokal veya private storage kullanılır.
- Public repoya gerçek VKN, TCKN, unvan, adres veya ticari tutar içeren ground truth
  **commit edilmez.**

### Opsiyonel provenance manifest (bu görevde oluşturulmaz)

İleride, public repoya **hassas veri içermeyen** bir manifest eklenebilir:

```json
{
  "labels_sha256": "<hash>",
  "document_count": 12,
  "schema_version": "v0.1",
  "created_at": "<ISO-8601 timestamp>"
}
```

Sınırlar açıkça belirtilir:

- Hash, belirli bir label sürümünün **sonradan değişmediğini** destekler.
- Annotator'ın model çıktısını görmediğini **tek başına kanıtlamaz.**
- Manifest **bu görevde oluşturulmaz.**
- Manifest **zorunlu bir freeze kriteri değildir.**

---

## 8. Schema freeze kriterleri

**Freeze kriterleri extraction accuracy veya `% ok` başarısına bağlı DEĞİLDİR.** Bir
şema, düşük ölçülmüş doğrulukla bile doğru şekilde temsil edici olabilir; freeze,
temsil edilebilirlik sorusudur.

En az **10 temsilî, kapsam içi gerçek fatura** üzerinde **anonim schema review** yapılır
(§9 coverage matrisi ile). v0.1 yalnızca şu **dört kriter** birlikte sağlandığında
frozen olabilir:

1. **Temsil edilebilirlik** — Belgelerde gözlenen her kritik bilgi, mevcut bir alanda ve
   mevcut veri tipiyle **kayıpsız** saklanabiliyor olmalı.
2. **Çözülmemiş boşluk olmaması** — Mevcut modele sığmayan her yapı ya şemaya eklenmiş
   ya da **açık gerekçeyle kapsam dışı** bırakılmış olmalı. Çözülmemiş bir schema gap
   kalmamalı.
3. **Format kapsamı** — Gözlenen her tarih ve sayı biçimi ya doğru parse edilmeli ya da
   açık biçimde desteklenmeyip `unreadable` durumuna düşmeli. **Sessiz yanlış parse
   kabul edilmez.**
4. **LineItem yeterliliği** — Beş alanlı LineItem modeli, örnek set üzerinde planlanan
   aritmetik kontroller için gerekli veriyi sağlayabilmeli.

> **Coverage matrisi** bu dört kriteri ölçmek için kullanılan **yöntemdir;** ayrı bir
> freeze kriteri değildir.

**Freeze kararı** şu üç kayıtla birlikte verilir:

- `docs/SCHEMA.md` durum güncellemesi (`DRAFT — NOT FROZEN` → frozen)
- `docs/DECISIONS.md` kararı
- Ayrı bir Git commit'i

> Bu görevde şema **freeze edilmez.** Şema durumu `DRAFT — NOT FROZEN` olarak kalır.

---

## 9. Schema coverage matrisi

Gerçek belge review aşamasında (§1 seviye A) kullanılacak önerilen tablolar. Burada
**boş** bırakılmıştır; gerçek veriyle bu görevde doldurulmaz.

**Header coverage:**

| Belge ID | Alan | Belgede var mı? | Gözlenen format | Mevcut tip temsil ediyor mu? | Parser destekliyor mu? | Schema gap | Not |
| -------- | ---- | --------------- | --------------- | ---------------------------- | ---------------------- | ---------- | --- |
| | | | | | | | |

**LineItem coverage:**

| Belge ID | Satır yapısı | Beş alan mevcut mu? | Çok satırlı açıklama | İskonto | Çoklu KDV | Model yeterli mi? | Gap |
| -------- | ------------ | ------------------- | -------------------- | ------- | --------- | ----------------- | --- |
| | | | | | | | |

**Kurallar:**

- Gerçek dosya adı kullanılmaz; **anonim belge ID** (`DOC-01`, `DOC-02`, …) kullanılır.
- Gerçek VKN, unvan, fatura numarası veya tutar **yazılmaz.**
- Coverage matrisi **extraction accuracy değildir** (§1 seviye A, pipeline gerektirmez).
- İnsan doğrudan orijinal belgeyi inceleyerek doldurur.

---

## 10. Yönsel hedefler (yalnızca header extraction)

Aşağıdaki başlangıç hedefleri **yalnızca header extraction** için geçerlidir ve
PROJECT_BRIEF §6/§10 ile hizalıdır:

| Hedef | Değer |
| ----- | ----- |
| Header value accuracy | ~%85 |
| Header numeric value accuracy | ~%90 |
| Valid structured output rate | ≥ %95 |
| Processing failure rate | ≤ %5 |

**Açıkça:**

- Bunlar **ölçülmüş sonuç değildir.**
- **Production SLA değildir.**
- **Seed set sonucu genellenemez.**
- **LineItem metriklerine uygulanmaz** (LineItem için sayısal hedef verilmemiştir).
- **Her oran ham sayılarla birlikte** raporlanır.
- **Küçük örneklemde** birkaç field instance sonucu ciddi biçimde değiştirebilir.

---

## 11. Seed ve final evaluation ayrımı

### Seed set

- Yaklaşık **8–12 temsilî belge.**
- Amaç: schema ve pipeline problemlerini **erken keşfetmek** ve error category
  keşfi yapmak.
- **Directional sonuç** üretir; production performansı **kanıtlamaz.**

### Daha geniş evaluation seti

- **Schema freeze sonrasında** etiketlenir.
- **Alan başına örnek sayısı** raporlanır.
- Aynı ground truth seti, model/provider karşılaştırmalarında **korunur.**
- Dataset ve schema sürümleri **kayıt altına alınır.**
- **Cost ve latency** raporlanır.

> **Ground-truth etiketleme, schema freeze öncesinde başlamaz.** Schema coverage review
> (§1 seviye A), ground-truth etiketleme **değildir** — biri temsil edilebilirliği,
> diğeri accuracy için referans veriyi üretir.

---

## 12. Pipeline metrikleri

Aşağıdaki metrikler, extraction/ingestion pipeline uygulandıktan **sonra** ölçülür.

### Valid structured output rate

Çıktının Pydantic `Invoice` şemasına başarıyla **validate edildiği** oran.

> Bu metrik **alan doğruluğunu kanıtlamaz;** yalnızca çıktının yapısal olarak geçerli
> olduğunu gösterir. Yapısal olarak geçerli bir `Invoice` yine de yanlış değerler
> içerebilir.

### Processing failure rate

Kullanılabilir bir `Invoice` sonucu **üretilemeyen** belgelerin oranı.

### Latency

Belge başına uçtan uca işleme süresi.

### Cost

Belge başına tahmini extraction maliyeti.

---

## İlgili belgeler

- Şema kontratı: [`docs/SCHEMA.md`](SCHEMA.md) (`DRAFT — NOT FROZEN`)
- Karar günlüğü: [`docs/DECISIONS.md`](DECISIONS.md) (D-022…D-032 bu belgeyi kapsar)
- Ürün kapsamı ve ölçüm notları: [`PROJECT_BRIEF.md`](../PROJECT_BRIEF.md) §6, §10
