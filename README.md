# DocumentFlow AI

Ticari faturaları işleyen; faturadan yapılandırılmış veri çıkaran, çıkarılan
veriyi deterministik kurallarla doğrulayan, şüpheli alanları insan incelemesine
yönlendiren ve onaylanmış sonucu JSON olarak dışa aktaran, insan denetimli ve
ölçülebilir bir belge işleme sistemi.

- Ürün tanımı ve MVP sınırları: [`PROJECT_BRIEF.md`](PROJECT_BRIEF.md)
- Teknik karar günlüğü: [`docs/DECISIONS.md`](docs/DECISIONS.md)
- Extraction şeması (DRAFT): [`docs/SCHEMA.md`](docs/SCHEMA.md)
- Extraction sözleşmesi (sağlayıcı bağımsız): [`docs/EXTRACTION.md`](docs/EXTRACTION.md)
- Validation kuralları (ruleset 0.1): [`docs/VALIDATION.md`](docs/VALIDATION.md)
- Deterministik review flagging: [`docs/FLAGGING.md`](docs/FLAGGING.md)
- Uçtan uca akış ve ürün yüzeyi: [`docs/WORKFLOW.md`](docs/WORKFLOW.md)
- Evaluation metodolojisi (DRAFT): [`docs/EVALUATION.md`](docs/EVALUATION.md)
- Veri toplama ve şema review: [`docs/DATA_COLLECTION.md`](docs/DATA_COLLECTION.md)

Depoda şu an bulunanlar: extraction şeması ve Türkçe parser'lar, deterministik
validation kuralları, sağlayıcıdan bağımsız extraction sözleşmesi, V1.0 PDF
ingestion kontrolleri, deterministik review flagging, kalıcı veri katmanı ve
uçtan uca çalışan bir review yüzeyi (yükle → çıkar → doğrula → düzelt → onayla →
JSON export → audit).

> **Henüz gerçek çıkarım yapılmamaktadır.** LLM sağlayıcı ve model seçimi
> bilinçli olarak ertelendi (D-049); uygulama `recorded` extractor ile çalışır ve
> yüklenen PDF ne olursa olsun aynı sentetik faturayı döndürür. Review ekranı bunu
> görünür bir uyarıyla bildirir. Bu nedenle **ölçülmüş bir doğruluk, gecikme veya
> maliyet iddiası bulunmamaktadır.**

## Proje yapısı

```text
backend/         FastAPI backend (ilk aktif uygulama)
docs/            Karar günlüğü ve dokümantasyon
compose.yaml     PostgreSQL geliştirme veritabanı (yalnızca DB servisi)
.env.example     Ortam değişkeni örneği (hem uygulama hem Compose için)
```

> `frontend/` klasörü, human review geliştirme aşamasında oluşturulacaktır
> (bkz. `docs/DECISIONS.md`, D-001).

## Veri gizliliği

Bu depo **public**'tir. Gerçek faturalar VKN/TCKN, şirket unvanı, adres ve ticari
tutarlar gibi hassas bilgiler içerebilir. Bu nedenle:

- **Gerçek belgeler ve ground-truth label dosyaları repoya commit edilmez.** Bunlar
  yalnızca lokal veya private storage'da tutulur.
- Bu karar, **gizlilik ve KVKK risklerini azaltmak** içindir (hukuki bir uygunluk
  garantisi değil, bilinçli bir risk azaltma tercihidir).
- **Testler yalnızca sentetik veya güvenli biçimde anonimleştirilmiş fixture** kullanır;
  gerçek fatura içeriği içermez.
- **Lokal veri klasörleri `.gitignore` ile dışlanır** (ör. `data/raw/`, `data/private/`,
  `datasets/raw/`, `*.local.pdf`).
- **`.env`, API anahtarları ve credential bilgileri commit edilmez** (yalnızca
  `.env.example` bulunur).
- **Dataset'in repoda bulunmaması bilinçli bir tasarım kararıdır**, eksiklik değildir
  (bkz. `docs/EVALUATION.md` ve `docs/DECISIONS.md`, D-029).

## Gereksinimler

- **Python 3.13** — proje hedef sürümü (`>=3.13,<3.14`). Python 3.14 proje
  ortamında kullanılmaz.
- [uv](https://docs.astral.sh/uv/) — ortam ve bağımlılık yönetimi.
- **Docker** — ayrı bir ön koşuldur ve yalnızca yerel PostgreSQL geliştirme
  veritabanı içindir. Docker kurulu değilse aşağıdaki `docker compose ...`
  komutları çalışmaz. `/health` ve testler için Docker **gerekmez**.

## Ortam değişkenleri

Tek `.env` dosyası proje kökünde bulunur ve hem uygulamayı (Pydantic Settings)
hem de Docker Compose PostgreSQL servisini besler. Örnek dosyayı kopyalayıp
değerleri gözden geçirin (gerçek `.env` Git'e eklenmez):

```powershell
# proje kökünde
Copy-Item .env.example .env
```

## PostgreSQL (opsiyonel — /health ve testler için gerekmez)

Docker kuruluysa, proje kökünde:

```powershell
docker compose config
docker compose up -d
docker compose ps
docker compose down
```

> Docker bu ortamda kurulu değilse yukarıdaki komutlar çalışmaz.

## Backend kurulum ve çalıştırma

`backend/` dizininde:

```powershell
uv python install 3.13
uv sync
uv run python --version
uv run uvicorn documentflow.main:app --reload
```

Ardından sağlık kontrolü:

```text
GET http://127.0.0.1:8000/health
# {"status": "ok"}
```

## Geliştirme komutları

`backend/` dizininde:

```powershell
uv run pytest                 # testler
uv run ruff check .           # lint
uv run ruff format --check .  # format kontrolü
uv run mypy src               # statik tip kontrolü
```

## Veritabanı migration'ları

Alembic altyapısı hazırdır; bu aşamada henüz migration üretilmemiştir.
Şema geliştirmesi başladığında migration'lar eklenecektir.
