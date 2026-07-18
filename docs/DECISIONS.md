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
