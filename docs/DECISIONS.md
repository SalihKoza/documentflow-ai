# Karar Günlüğü (Decision Log)

Bu dosya, DocumentFlow AI projesinde alınan **küçük ve orta ölçekli teknik kararları** tek yerde, kısa ve takip edilebilir biçimde tutar. Amaç, her karar için ayrı bir ADR (Architecture Decision Record) dosyası üretmeden, kararları tek bir tabloda biriktirmektir.

Ayrı ADR dosyaları yalnızca **sonradan değiştirilmesi yüksek maliyetli veya ayrıntılı gerekçe gerektiren kritik mimari kararlar** için kullanılır. Bu tür kararların ölçütleri "ADR Gerektiren Kararların Ölçütleri" bölümünde açıklanmıştır.

---

## Karar Kayıt Formatı

Kararlar, aşağıdaki sütunlara sahip tek bir Markdown tablosunda tutulur. Yeni bir karar alındığında, "Mevcut Kararlar" tablosuna yeni bir satır eklenir.

| Sütun | Açıklama |
| ----- | -------- |
| **ID** | Artan biçimde verilen kimlik: `D-001`, `D-002`, ... |
| **Tarih** | Kararın alındığı tarih (YYYY-AA-GG). |
| **Durum** | Kararın güncel durumu. |
| **Karar** | Alınan kararın tek cümlelik özeti. |
| **Kısa gerekçe** | Kararın neden alındığının kısa açıklaması. |
| **Yeniden değerlendirme koşulu** | Kararın tekrar gözden geçirilmesini gerektiren koşullar. |

**Durum değerleri:**

- `Kabul edildi` — Başlangıç durumu; karar geçerlidir.
- `Değiştirildi` — Karar sonradan güncellenmiştir (yeni kararı ayrı bir satır olarak eklemek önerilir).
- `İptal edildi` — Karar artık geçerli değildir.

---

## Mevcut Kararlar

| ID | Tarih | Durum | Karar | Kısa gerekçe | Yeniden değerlendirme koşulu |
| -- | ----- | ----- | ----- | ------------ | ---------------------------- |
| D-001 | 2026-07-17 | Kabul edildi | Hafif iki bölümlü tek repo kullanılacak. | Extraction, validation ve evaluation çalışmalarına öncelik vermek; frontend ve monorepo araçlarının erken öğrenme yükünü önlemek; minimum karmaşıklık ilkesini korumak. | Frontend uygulaması oluşturulurken, backend ve frontend arasında ortak şema paylaşımı gerektiğinde veya birden fazla bağımsız uygulama/paket ortaya çıktığında. |
| D-002 | 2026-07-17 | Kabul edildi | Backend dili Python olacaktır. | Ingestion, extraction, validation, evaluation ve ölçüm ile FastAPI için olgun ve uygun bir ekosistem sunar. | Frontend dili ayrı bir karar olarak değerlendirilecek; gerçek bir dil/ekosistem uyumsuzluğu veya ihtiyaç doğarsa. |
| D-003 | 2026-07-17 | Değiştirildi | Python sürümü `3.14`; proje ve bağımlılık yönetimi `uv`. (D-013 ile değiştirildi.) | Modern sürüm; `uv` ile hızlı, tekrarlanabilir sanal ortam, bağımlılık yönetimi ve lockfile. | Ekosistem ve bağımlılık uyumunu netleştirmek için hedef sürüm Python 3.13'e sabitlendi; bkz. D-013. |
| D-004 | 2026-07-17 | Kabul edildi | Backend framework FastAPI olacaktır (yalnızca API/transport katmanı). | Hızlı API geliştirme ve Pydantic entegrasyonu; çekirdek iş mantığı framework'ten bağımsız kalır. | Transport/arayüz ihtiyaçları FastAPI'nin kapsamını aşarsa. |
| D-005 | 2026-07-17 | Kabul edildi | Kalıcı veri için PostgreSQL kullanılacaktır (tek instance). | İlişkisel bütünlük ve JSON desteği; metadata, extraction, validation ve audit verileri için uygundur. | Ölçülen bir ölçek, replikasyon veya performans ihtiyacı ortaya çıkarsa. |
| D-006 | 2026-07-17 | Kabul edildi | Veri erişimi: SQLAlchemy 2 + Alembic + psycopg 3, başlangıçta senkron. | Olgun ORM ve migration; erken async karmaşıklığından kaçınmak. | Ölçülen gerçek bir eşzamanlılık ihtiyacı doğunca async veri erişimine geçilecektir. |
| D-007 | 2026-07-17 | Kabul edildi | Test framework `pytest` olacaktır. | Yaygın ve sade; saf validation fonksiyonları, endpoint'ler ve use-case'ler için uygundur. | Gerekirse. |
| D-008 | 2026-07-17 | Kabul edildi | Lint ve formatlama aracı `Ruff` olacaktır. | Hızlı; lint, import düzeni ve formatlamayı tek araçta toplar. | Gerekirse. |
| D-009 | 2026-07-17 | Kabul edildi | Statik tip kontrolü `mypy` (başlangıçta esnek ayarlar). | Yeni kodda tip disiplini; aşırı katılıktan kaçınmak. | Kod olgunlaştıkça katılık kademeli olarak artırılacaktır. |
| D-010 | 2026-07-17 | Kabul edildi | PostgreSQL Docker Compose'da; FastAPI host üzerinde çalışır. | İzole, tekrarlanabilir veritabanı; backend'i erken container'lamamak. | Dağıtım veya CI ihtiyacı doğunca backend containerization değerlendirilecektir. |
| D-011 | 2026-07-17 | Kabul edildi | Configuration yönetimi Pydantic Settings (APP_ENV, LOG_LEVEL, DATABASE_URL). | Merkezi, tip güvenli config; secret'ları koddan ve Git'ten ayırmak. | Secret yönetimi karmaşıklaşırsa (ör. vault/gizli yönetim) yeniden değerlendirilecektir. |
| D-012 | 2026-07-17 | Kabul edildi | Backend `src` layout; Python paket adı `documentflow`. | Import hijyeni; yalnızca gerçek ihtiyaç bulunan modüllerle sade başlangıç. | Yeni çekirdek modüller (extraction, validation, review) eklenince yapı genişletilecektir. |
| D-013 | 2026-07-17 | Kabul edildi | Python sürümü `3.13` (`>=3.13,<3.14`); proje ve bağımlılık yönetimi `uv`. | Olgun ve yaygın desteklenen sürüm; `uv` ile hızlı, tekrarlanabilir sanal ortam, bağımlılık yönetimi ve lockfile. D-003'ün yerini alır. | Bir bağımlılık Python 3.13 ile gerçek bir uyumsuzluk gösterirse hedef sürüm yeniden değerlendirilecektir. |
| D-014 | 2026-07-18 | Kabul edildi | Line item'lar (fatura kalemleri) extraction şeması v0.1'e dahildir. | Satır bazlı doğrulama (satır tutarı = miktar × birim fiyat) ve toplam tutarlılığı için kalem verisi gereklidir; şemanın gerçek değeri validation'dadır. | Kalem yapısının gerçek faturalarda öngörülenden karmaşık (iskonto, çok oranlı) çıkması durumunda. |
| D-015 | 2026-07-18 | Kabul edildi | Her extraction alanı ham (`raw`) ve parse edilmiş (`value`) değeri, üç durumlu `status` ile birlikte `FieldValue[T]` içinde saklar. | İzlenebilirlik ve insan denetimi: hangi ham metnin hangi değere çevrildiği ve durumu görünür olmalı. | İzlenebilirlik ihtiyaçları değişirse veya ek alan gerekirse. |
| D-016 | 2026-07-18 | Kabul edildi | Alan durumu üç değerlidir: `ok`, `missing`, `unreadable` (yapısal invariant'larla). | Eksik alan ile okunamayan alanı ayırmak, deterministik yönlendirme (flagging) için gereklidir; bunlar business değil yapısal kurallardır. | OCR/vision ingestion (V1.1) "raw'sız unreadable" gibi yeni durum ihtiyacı doğurursa. |
| D-017 | 2026-07-18 | Kabul edildi | Tüm sayısal ve parasal alanlar `Decimal` kullanır; `float` kabul edilmez. | Parasal kesinlik; `Decimal(float)` ikili yuvarlama hatasını kalıcı kılar. Sayısal alanlarda float girişi reddedilir. | Gerekirse (kesinlik gereksinimi değişmedikçe geçerli). |
| D-018 | 2026-07-18 | Kabul edildi | `LineItem` yalnızca beş alan içerir: `aciklama`, `miktar`, `birim_fiyat`, `kdv_orani`, `satir_tutari`. | "Az ama sağlam" ilkesi; erken kapsam genişlemesini önlemek. Ekstra alanlar (birim, iskonto, satır KDV tutarı) v0.1 dışıdır. | Gerçek faturalar ek alanı zorunlu kılarsa (sürüm artırımıyla). |
| D-019 | 2026-07-18 | Kabul edildi | Kalemler `kalemler: FieldValue[list[LineItem]]` olarak temsil edilir; container `raw`'ı tablo metnidir. | Aynı `FieldValue` mekanizmasını yeniden kullanır (yeni kavram yok); container düzeyinde ok/missing/unreadable ve audit ham metni sağlar. | Kalem container semantiği (ör. kısmi okunabilirlik) daha ince ayrım gerektirirse. |
| D-020 | 2026-07-18 | Kabul edildi | Türkçe sayı/tarih parser'ları saf ve status-agnostiktir; başarısızlıkta `None` döner, `FieldStatus` üretmez. | Parser'lar bağımsız birim test edilebilir kalır; ham metni duruma çevirmek extraction katmanının işidir. Parse edilememe normal kontrol akışıdır (istisna değil). | Evaluation hata kategorileri için parser'ın başarısızlık sebebi taşıması gerekirse. |
| D-021 | 2026-07-18 | Kabul edildi | Extraction şeması v0.1, gerçek Türkçe fatura örnekleriyle doğrulanmadan DONDURULMAZ (DRAFT). | Şema donmadan ground-truth etiketleme yapılırsa, şema değişince etiketler çöpe gider; freeze ayrı bir şema review adımında verilecektir. | Gerçek örneklerle doğrulama tamamlanıp ayrı bir şema review adımı freeze kararı verdiğinde. |
| D-022 | 2026-07-20 | Kabul edildi | Header ve LineItem metrikleri ayrı tablolarda raporlanır; tek bir birleşik "overall accuracy" üretilmez. | Header ve satır kalemleri farklı yapı ve hata modlarına sahiptir; birleştirilmiş tek sayı, kaynağı gizleyerek yanıltıcı olur. | Kullanıcı/portföy raporlaması birleşik bir üst metrik zorunlu kılarsa (yine de ham sayılarla). |
| D-023 | 2026-07-20 | Kabul edildi | Value accuracy ve status accuracy ayrı metriklerdir; ayrı raporlanır. | İki farklı soruyu (değer doğru mu? / durum sınıflandırması doğru mu?) yanıtlarlar ve paydaları farklıdır; birleştirmek her ikisini de bulanıklaştırır. | Metrik tüketicileri farklı bir kırılım isterse. |
| D-024 | 2026-07-20 | Kabul edildi | Value accuracy paydası, ground truth'ta mevcut ve okunabilir field instance'lardır. | Belgede olmayan veya gerçekten okunamayan alanlar için "değer doğruluğu" tanımsızdır; bunları paydaya katmak metriği çarpıtır. | Okunabilirlik tanımı gerçek veride belirsizleşirse annotation guide ile netleştirilir. |
| D-025 | 2026-07-20 | Kabul edildi | Status accuracy paydası, şemadaki tüm etiketlenmiş field slotlarıdır (belgede olmayanlar dahil). | Durum sınıflandırması (ok/missing/unreadable) tam da yokluk/okunamazlık durumlarını kapsamalıdır; bunlar paydadan çıkarılamaz. | Slot tanımı (ör. opsiyonel alanlar) değişirse. |
| D-026 | 2026-07-20 | Kabul edildi | Yanlış değer, kaçırılan alan, false positive ve unreadable ayrı hata kategorileridir; aynı sınıfta sayılmaz. | Bu hatalar davranışsal olarak farklıdır ve farklı düzeltmeler gerektirir; tek "hata" sayısı kök neden analizini engeller. | Kategori kümesi gerçek hata dağılımıyla incelenip genişletilebilir/sadeleştirilebilir. |
| D-027 | 2026-07-20 | Kabul edildi | Metin alanı karşılaştırması Unicode + Türkçe case + whitespace normalizasyonu kullanır; noktalama/unvan kısaltması normalleştirilmez. | Tam string eşleşmesi PDF whitespace ve Türkçe İ/I ile başarısız olur; agresif normalizasyon ise false match riski taşır. Naif `.lower()`/`.casefold()` Türkçe için yetersizdir. | Gerçek veride düzenli unvan/noktalama varyasyonu gözlenirse alan-spesifik normalizasyon gerekçeyle eklenir. |
| D-028 | 2026-07-20 | Kabul edildi | Ground truth, extraction/model çıktısından bağımsız olarak yalnızca orijinal belgeye bakılarak hazırlanır ve sürüm kilitlenir. | Model çıktısını görerek etiketleme, ölçümü modele doğru yanlı hale getirir (anchoring). Tek kişilik projede bağımsızlık zaman+erişim ayrımıyla korunur. | İkinci reviewer veya adjudication süreci eklenmesi gerekirse. |
| D-029 | 2026-07-20 | Kabul edildi | Gerçek belgeler ve ground-truth label dosyaları public repoya girmez; lokal/private tutulur. | Public repo'da gerçek VKN/TCKN/unvan/adres/tutar bulundurmak gizlilik ve KVKK riski yaratır; risk azaltma bilinçli tasarım kararıdır. | Anonimleştirme veya private dataset barındırma stratejisi netleşirse (yine gerçek PII olmadan). |
| D-030 | 2026-07-20 | Kabul edildi | Tüm yüzdeler ham sayılarla (pay/payda) birlikte raporlanır; yalnızca yüzde kabul edilmez. | Küçük seed set'te birkaç instance yüzdeyi ciddi değiştirir; ham sayılar olmadan yüzde yanıltıcıdır ve production iddiası izlenimi verir. | (Kalıcı ilke; değişmesi beklenmez.) |
| D-031 | 2026-07-20 | Kabul edildi | Schema freeze, extraction accuracy'ye değil dört temsil edilebilirlik kriterine dayanır (temsil edilebilirlik, çözülmemiş boşluk yok, format kapsamı, LineItem yeterliliği). | Şema doğru temsil ediyorsa düşük ölçülmüş doğrulukla bile dondurulabilir; accuracy'ye bağlamak yanlış bir kapı olur. Coverage matrisi yöntemdir, ayrı kriter değil. | En az 10 temsilî gerçek fatura üzerinde anonim review dört kriteri sağladığında freeze kararı ayrı commit ile verilir. |
| D-032 | 2026-07-20 | Kabul edildi | LineItem evaluation üç kademelidir: (1) satır sayısı, (2) aritmetik tutarlılık, (3) pozisyonel alan doğruluğu (yalnızca K1 geçerse). | Satır sayısı eşleşmeden pozisyonel karşılaştırma anlamsızdır; zorla hizalama uydurma sonuç üretir. Kademeler kısmi bilgiyi korur. | Semantic/fuzzy alignment ihtiyacı doğar veya kademe tanımları gerçek veride yetersiz kalırsa. |
| D-033 | 2026-07-22 | Kabul edildi | Validation katmanı saf ve framework-bağımsızdır; tek giriş noktası `validate_invoice(invoice) -> ValidationReport`'tur ve generic rule engine, plugin sistemi veya kural DSL'i oluşturulmaz. | Kurallar sabit ve okunabilir bir sırada çağrılınca hem determinizm hem izlenebilirlik bedelsiz gelir; motor soyutlaması bugün var olmayan bir esneklik ihtiyacına karşılık gelirdi (minimum karmaşıklık). | Kuralların çalışma zamanında (ör. kullanıcı başına) yapılandırılması gerçek bir ihtiyaç hâline gelirse. |
| D-034 | 2026-07-22 | Kabul edildi | Severity iki değerlidir (`error`, `warning`); `review_required` rapor düzeyinde türetilir ve validation çıktısı hiçbir confidence/olasılık alanı içermez. | `severity` kusurun türünü, `review_required` yönlendirmeyi anlatır; ikisini tek alanda birleştirmek her ikisini de bulanıklaştırır. Confidence yasağı PROJECT_BRIEF §5 kararının doğrudan uygulanmasıdır. | Otomatik onay/export akışı eklendiğinde error'ın bloklayıcı rolü ayrıca tanımlanacaktır. |
| D-035 | 2026-07-22 | Kabul edildi | Değerlendirilemeyen kurallar `findings` içinde değil, ayrı bir `not_evaluated` listesinde tutulur; yalnızca girdi yokluğu kaydedilir, kaskad atlamalar kaydedilmez. | "Kural çalıştı ve geçti" ile "kural hiç çalışamadı" ayrımı korunmalıdır; aynı kaydı findings'e koymak listenin "problem" anlamını kaybettirirdi. Kaskad kayıtları ise zaten raporlanmış bir hatayı ikinci kez yazardı. | Review arayüzü değerlendirilemeyen kuralları da yönlendirme sinyali sayarsa. |
| D-036 | 2026-07-22 | Kabul edildi | Bulgular tek bir `field_paths` tuple'ı taşır (ilk eleman anchor); yol formatı `header.<alan>` ve `kalemler[i].<alan>`'dır ve yolda `.value` bulunmaz. | Çok alanlı kurallarda (ör. `ara_toplam + kdv_toplam = genel_toplam`) hangi alanın yanlış olduğu bilinemez; tüm ilgili alanları taşımak dürüst, anchor'ı ilk elemana koymak arayüz için yeterlidir. Yol bir alan adresidir, Pydantic attribute zinciri değil. | Şema freeze'inde alan adları değişirse yollar güncellenir (rule ID'ler değişmez). |
| D-037 | 2026-07-22 | Kabul edildi | Bulgu sırası inşa yoluyla deterministiktir (header → toplam aritmetiği → satırlar index artan → satır toplamı); rapor sonradan sıralanmaz. | Uygulama sırası belge okuma sırasına karşılık gelir ve insan denetimi için `rule_id`'ye göre sıralamaktan daha anlamlıdır; determinizm ek bir sıralama adımı olmadan zaten sağlanır. | Tüketici farklı bir sıralama isterse bu, sunum katmanında yapılır. |
| D-038 | 2026-07-22 | Kabul edildi | Aritmetik karşılaştırmalar `Decimal` ile tam eşitliktir; v0.1'de tolerance veya yuvarlama kuralı tanımlanmaz. | Gerçek fatura verisi görülmeden seçilecek her eşik uydurma olurdu ve gerçek tutarsızlıkları gizleme riski taşırdı (`docs/EVALUATION.md` §4 ile aynı duruş). Bilinen bedeli, kuruş yuvarlaması yapılmış satırlarda false positive üretmesidir. | Gerçek faturalarda düzenli yuvarlama farkı gözlenirse, gerekçeli ayrı bir karar olarak tolerance eklenir. |
| D-039 | 2026-07-22 | Kabul edildi | İzin verilen KDV oranı kümesi `{1, 10, 20}`'dir, ruleset sürümüne bağlıdır ve kapsam dışı oran `error` değil `warning` üretir. | Küme bir v0.1 kapsam kısıtıdır, yasa gereği imkânsızlık değil: %0 istisna ve 2023 öncesi %8/%18 meşru olabilir. Bunlara "veri kesin yanlış" demek yanlış olurdu; insan denetimine yönlendirmek yeterlidir. | Mevzuat değişirse veya faturanın tarihine göre dönemsel oran kontrolü gerekirse (ruleset sürümü artırılarak). |
| D-040 | 2026-07-22 | Kabul edildi | `fatura_no` biçim sapması hiçbir koşulda hard fail üretmez; e-Fatura kalıbından (3 harf + 13 rakam) sapma `warning`'dir ve `missing`/`unreadable` durumundan ayrı ele alınır. | Kâğıt faturaların serbest seri/sıra biçimi geçerlidir; biçim sapmasını error saymak meşru belgeleri reddetmek olurdu. Alanın yokluğu ile biçim sapması farklı sorunlardır ve farklı düzeltme gerektirir. | e-Fatura dışı belgeler kapsam dışına çıkarılırsa. |
| D-041 | 2026-07-22 | Kabul edildi | Extraction katmanı sağlayıcıdan bağımsızdır; arayüz `ExtractorProtocol` (ABC değil `typing.Protocol`) ve sağlayıcı hataları istisna olarak sızmaz, `ExtractionStatus` değerlerine çevrilir. | Protocol yapısal tiplemedir: adapter'lar domain'den türemek zorunda kalmaz, sahteler mirassız yazılır. Hataların sonuç tipine çevrilmesi çağıranı sürpriz istisnalardan korur ve her başarısızlık senaryosunu test edilebilir kılar. | Akış senkron çağrının ötesine geçerse (streaming, batch) arayüz genişletilir. |
| D-042 | 2026-07-22 | Kabul edildi | Sağlayıcı yanıtı ayrı bir wire DTO ile karşılanır; DTO'da tüm sayısal alanlar `str`'dir ve tüm DTO'lar `extra="forbid"` taşır. | JSON sayısı Python'da `float` olur ve D-017'nin Decimal korumasını bozardı; sayıyı metin olarak istemek tüm zinciri float'tan uzak tutar. `extra="forbid"`, sağlayıcının gönderdiği `confidence` gibi alanların sessizce yutulmasını değil fark edilmesini sağlar (PROJECT_BRIEF §5). | Sağlayıcı structured output garantisi wire sözleşmesini gereksiz kılarsa. |
| D-043 | 2026-07-22 | Kabul edildi | Provider metadata (model, prompt sürümü, latency, token, tahmini maliyet) domain `Invoice` modelinden ayrı tutulur ve `ExtractionResult` üzerinde taşınır. | Domain modeli belgeden çıkarılan veriyi temsil eder; çalışma bilgisi oraya karışırsa sağlayıcı değiştiğinde şema kontratı da değişir. Ayrılık, ölçüm alanlarını sağlayıcı seçilmeden de anlamlı kılar. | Persistence katmanı metadata'yı ayrı bir tabloya taşırsa (model yine ayrı kalır). |
| D-044 | 2026-07-22 | Kabul edildi | Sağlayıcı bir alan için `ok` dediği hâlde değer parse edilemiyorsa alan `unreadable`'a düşürülür ve yolu `parse_failures`'a yazılır; değer tahmin edilmez. | `docs/EVALUATION.md` §1 seviye B "sessiz yanlış parse kabul edilmez" der. Düşürme, hatayı görünür kılar; ayrı liste ise "model okuyamadı" ile "model okudum dedi ama çeviremedik" ayrımını korur — ikisi farklı inceleme davranışı gerektirir. | Parser kapsamı genişleyip düşürme oranı anlamsızlaşırsa. |
| D-045 | 2026-07-22 | Kabul edildi | `error_detail` yalnızca alan yolu ve kararlı hata kodundan üretilir; Pydantic'in `msg`/`input` alanları kullanılmaz. | Doğrulama hataları varsayılan olarak girdi değerlerini — yani belge içeriğini — taşır. Hata metni log'a, rapora ve hata izleme sistemlerine gider; oraya fatura içeriği sızmamalıdır (D-029 ile aynı gerekçe). | (Kalıcı ilke.) |
| D-046 | 2026-07-22 | Kabul edildi | V1.0 ingestion belgeyi zincirin başında kabul/ret eder (imza, boyut, şifreleme, metin katmanı); metin katmanı kontrolü için `pypdf` bağımlılığı eklenir. | Kapsam dışı belgeyi sağlayıcıya göndermek "çıkarım kötü çalıştı" ile "belge kapsam dışı" ayrımını yok eder ve boşuna maliyet üretir. `pypdf` saf Python, bağımlılıksız ve MIT; `pdfplumber` (pdfminer.six + Pillow) ve `PyMuPDF` (AGPL + C eklentisi) bu tek iş için ağır kalır. | V1.1'de OCR/vision ingestion eklendiğinde kapsam kapısı yeniden tanımlanır. |
| D-047 | 2026-07-22 | Kabul edildi | Ham PDF dosya sisteminde içerik adresli (SHA-256) olarak saklanır; veritabanı yalnızca metadata ve göreli yol tutar (PostgreSQL `bytea` değil). | Gerçek faturalar zaten `data/private/` altında ve `.gitignore` ile dışlı (D-029); belge baytlarının DB yedeklerine ve dökümlerine girmemesi bu politikayla hizalıdır. Tek kullanıcı/tek belge ölçeğinde `bytea`'nın tek gerçek avantajı (atomiklik) karşılığında ödenen bedel orantısız. İçerik adresleme ayrıca path traversal yüzeyini yapısal olarak kapatır. | Çok kullanıcılı veya dağıtık bir dağıtım gerekirse object storage değerlendirilir (dosya sistemi çözümü sarmalanarak). |
| D-048 | 2026-07-22 | Kabul edildi | Review flag'leri yalnızca alan durumları ve validation raporundan türetilir; `ReviewFlag` hiçbir confidence/olasılık/skor alanı taşımaz ve v0.1'de birleşik risk skoru üretilmez. | PROJECT_BRIEF §5'in doğrudan uygulaması. `review_required` "bakılmalı mı", `severity` "ne kadar ciddi" sorusunu zaten yanıtlıyor; üçüncü bir türetilmiş sayı bugün hiçbir soruyu yanıtlamıyor ve kalibre edilmiş olasılık izlenimi verme riski taşıyor. | Yeterli etiketli veri ve kullanıcı düzeltmesi biriktiğinde tamamen deterministik bir skor değerlendirilebilir. |
| D-049 | 2026-07-22 | Kabul edildi | Vision-capable LLM sağlayıcı ve model seçimi ertelendi; bu fazda gerçek adapter yazılmadı, `anthropic` benzeri bir SDK bağımlılığı eklenmedi. | Extraction sözleşmesi (D-041–D-045) bir sağlayıcı olmadan da eksiksiz kurulup test edilebiliyor; ertelemenin mümkün olması sağlayıcı bağımsızlığının kanıtıdır. Erken bağlanmak, seçim değiştiğinde atılacak kod üretirdi. | Model kararı verildiğinde tek modüllük adapter eklenir; sözleşme ve dönüşüm yolu değişmez. |
| D-050 | 2026-07-22 | Kabul edildi | Human review yüzeyi minimal FastAPI + server-rendered HTML olacaktır (CLI + statik rapor değil); SPA, React ve çok kullanıcılı yapı kurulmaz. | PROJECT_BRIEF §3 akışı bir review EKRANI ve orada "düzelt ve onayla" adımı tanımlıyor; CLI bu ergonomiyi karşılayamaz. FastAPI zaten D-004 ile seçilmiş transport katmanıdır, dolayısıyla eklenen yüzey ince kalır. Test edilebilirlik korunur: rotalar TestClient ile sürülür ve HTML iddiaları alan kimlikleriyle sınırlı tutulur. | Review ihtiyaçları form tabanlı akışı aşarsa (canlı doğrulama, PDF üzerinde işaretleme) ayrı bir frontend değerlendirilir (D-001). |
| D-051 | 2026-07-22 | Kabul edildi | Çıkarılan `Invoice` anlık görüntüsü normalize kolonlar yerine tek bir JSONB alanında saklanır. | `FieldValue` üçlüsü alan başına üç kolon demek olurdu ve şema hâlâ DRAFT (D-021) — her şema değişikliği migration gerektirirdi. Snapshot'ın amacı sorgulanabilirlik değil audit doğruluğudur: çıkarımın o anki hâlini birebir korumak. | Alan bazlı sorgulama/raporlama gerçek bir ihtiyaç hâline gelirse JSONB üzerinde indeks veya türetilmiş tablo eklenir. |
| D-052 | 2026-07-22 | Kabul edildi | Audit olayları append-only'dir ve `id` (identity) ile sıralanır; `occurred_at` sıralama için kullanılmaz. | PostgreSQL'de `now()` işlem başlangıç zamanıdır: aynı işlemde yazılan olaylar aynı damgayı alır ve zaman damgasına göre sıralama belirsiz olur. Identity anahtarı yazılma sırasını kesin biçimde korur. Güncelleme/silme yolu açılmaz. | Olay hacmi arşivleme gerektirirse (bu ölçekte beklenmiyor). |
| D-053 | 2026-07-22 | Kabul edildi | Onaylanmamış veri dışa aktarılamaz; reddedilen export denemesi de audit'e yazılır ve hiçbir veri üretilmez. | Onay, insan denetiminin sistemdeki tek kanıtıdır; onaysız export bu denetimi anlamsız kılardı. Reddedilen denemenin kaydedilmesi, "kim ne zaman denedi" sorusunu yanıtlanabilir tutar. | (Kalıcı ilke.) |
| D-054 | 2026-07-22 | Kabul edildi | Orijinal çıkarım anlık görüntüsü hiçbir zaman güncellenmez; düzeltmeler ayrı satırlara, onaylanan sonuç ayrı bir anlık görüntüye yazılır. | "Model ne üretti" ile "insan neyi onayladı" iki ayrı sorudur ve ikisi de sonradan yanıtlanabilir olmalıdır. Yerinde güncelleme, extraction accuracy ölçümünün referansını yok ederdi (`docs/EVALUATION.md`). | (Kalıcı ilke.) |
| D-055 | 2026-07-22 | Kabul edildi | V1.0 kapsam kapısından geçemeyen belge diske yazılmaz; yalnızca metadata ve ret nedeni kaydedilir. | Kapsam dışı veya PDF olmayan içeriği biriktirmek gereksiz saklama riski üretir. Ret nedeni zaten teşhis için yeterlidir. | Reddedilen belgelerin incelenmesi gereken bir hata ayıklama ihtiyacı doğarsa, açıkça sınırlı bir karantina alanı değerlendirilir. |
| D-056 | 2026-07-22 | Kabul edildi | Veritabanı entegrasyon testleri gerçek PostgreSQL'e karşı çalışır; SQLite kullanılmaz. Veritabanı erişilemezse bu testler atlanır, çekirdek suite veritabanısız yeşil kalır. | SQLite'ın nativ `DECIMAL`i yoktur ve SQLAlchemy değerleri float üzerinden taşır — bu D-017'yi sessizce ihlal eder ve JSONB davranışı hiç sınanmaz. Atlama mekanizması, çekirdek mantığın veritabanından bağımsız kalması kuralını da korur. | CI ortamı eklenirse PostgreSQL servisi zorunlu kılınır ve atlama kaldırılır. |
| D-057 | 2026-07-23 | Kabul edildi | Export yan etkili bir işlemdir (`export_records` satırı + `export_created` audit olayı) ve yalnızca `POST /runs/{id}/export` ile tetiklenir; GET rotalarının tamamı safe kalır. | Browser prefetch, tekrar tıklama veya otomatik link taraması kazara export üretmemelidir; export, insan denetiminin audit'e yazılan kanıtıdır. Davranışı belgelemek HTTP semantiğini değiştirmez. Review ekranında export bu nedenle link değil, POST formudur. | (Kalıcı ilke.) Yan etkisiz bir "önizleme" ihtiyacı doğarsa, kayıt üretmeyen ayrı bir GET rotası değerlendirilir. |

### D-001 — Açıklama ve sınırlar

Bu karar, projenin repo yapısını mümkün olan en sade biçimde tutmayı amaçlar. Kararın kapsamı ve sınırları:

- Kavramsal yapı ileride `backend/`, `frontend/` ve `docs/` alanlarından oluşabilir.
- Backend, ilk aktif uygulama olacaktır.
- Frontend, human review geliştirme aşamasında oluşturulacaktır.
- Bu aşamada boş bir `frontend/` klasörü oluşturulmayacaktır.
- Monorepo yönetim aracı kullanılmayacaktır.
- Ortak paket veya shared schema altyapısı başlangıçta kurulmayacaktır.
- Backend ve frontend ayrı repolara bölünmeyecektir.

### D-003 — Açıklama ve sınırlar (geçmiş)

Bu karar **D-013 ile değiştirilmiştir**. Başlangıçta hedef Python sürümü `3.14`
olarak belirlenmişti; ekosistem ve bağımlılık uyumunu netleştirmek için hedef
sürüm Python `3.13`'e sabitlenmiştir. Güncel karar için bkz. D-013.

### D-013 — Açıklama ve sınırlar

- Hedef Python sürümü `>=3.13,<3.14` aralığına sabitlenmiştir; proje ortamında
  Python 3.14 kullanılmaz.
- `uv`; sanal ortam, runtime ve development bağımlılık yönetimi, lockfile
  oluşturma ve test/kalite komutlarını çalıştırmak için kullanılır.
- Her yeni bağımlılık eklenirken Python 3.13 uyumluluğu kontrol edilir.
- Gerçek bir uyumsuzluk çıkarsa Python sürümü sessizce değiştirilmez; durum
  belgelenip yeniden değerlendirilir.

### D-005 — Açıklama ve sınırlar

- Başlangıçta tek PostgreSQL veritabanı; replica ve clustering yok.
- Erken performans optimizasyonu yapılmaz; ihtiyaç olmadan gelişmiş PostgreSQL
  özellikleri kullanılmaz.
- Raw PDF dosyalarının veritabanında mı yoksa dosya sisteminde mi tutulacağı
  daha sonra kararlaştırılacaktır.

### D-006 — Açıklama ve sınırlar

- ORM modelleri ile FastAPI request/response modelleri ayrı tutulur.
- Gereksiz generic repository katmanı veya her tablo için otomatik CRUD
  sistemi oluşturulmaz.
- Alembic migration'ları çalıştırılmadan önce okunup kontrol edilir.
- Gerçek bir eşzamanlılık ihtiyacı ölçülmeden async veri erişimine geçilmez.

### D-010 — Açıklama ve sınırlar

- Docker yalnızca PostgreSQL ortamını izole ve tekrarlanabilir kılmak için
  kullanılır.
- Backend bu aşamada container'lanmaz; host üzerinde çalışır.

### D-011 — Açıklama ve sınırlar

- Gerçek `.env` dosyası Git'e eklenmez; repoda yalnızca `.env.example` bulunur.
- Secret değerleri koda, karar veya dokümantasyon dosyalarına yazılmaz.
- Settings katmanı yalnızca configuration okur, iş mantığı içermez.
- Testler gerçek API anahtarlarına bağımlı olmaz.

### D-012 — Açıklama ve sınırlar

- İlk iskelette yalnızca gerçek ihtiyaç bulunan modüller oluşturulur.
- Extraction, validation, audit ve review modülleri ilgili aşamalarda eklenir.
- Boş veya varsayımsal klasörler, generic repository veya service base
  sınıfları oluşturulmaz.

---

## ADR Gerektiren Kararların Ölçütleri

Aşağıdaki türdeki kararlar, gerektiğinde ayrı bir ADR dosyası olarak belgelenebilir:

- Değiştirilmesi yüksek maliyetli kararlar.
- Birden fazla ciddi alternatif arasından yapılan seçimler.
- Sistemin temel mimarisini etkileyen kararlar.
- Güvenlik, veri bütünlüğü veya uzun vadeli bakım üzerinde önemli etkisi bulunan kararlar.
- Mülakatta veya teknik incelemede ayrıntılı biçimde savunulması gereken kararlar.

Aşağıdaki türdeki tercihler için **ayrı ADR oluşturulmaz**; bunlar yalnızca bu karar günlüğüne kaydedilir (gerekirse):

- Klasör isimleri.
- Küçük araç seçimleri.
- Kolayca geri alınabilir ayarlar.
- Geçici geliştirme tercihleri.
