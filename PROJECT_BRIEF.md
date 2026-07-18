# DocumentFlow AI — Proje Özeti (Project Brief)

Bu belge, DocumentFlow AI projesinin problem tanımını, MVP (Minimum Uygulanabilir Ürün) sınırlarını ve sonradan kabul edilen proje kararlarını tanımlar. Bu aşamada yalnızca ürün kapsamı, kabul edilen kararlar ve yönlendirici ilkeler dokümante edilir; kod, klasör yapısı, teknoloji seçimi veya mimari oluşturulmaz.

---

## 1. Problem Tanımı

Muhasebe ve ofis personeli, faturalardaki bilgileri elle okuyup sistemlere aktarmak için önemli miktarda zaman harcar. Bu manuel süreç yavaştır, hataya açıktır ve tekrar eden bir yük oluşturur.

DocumentFlow AI, tek bir faturadan yapılandırılmış veriyi otomatik olarak çıkararak bu yükü azaltmayı amaçlar. Sistem, çıkarılan veriyi deterministik doğrulama (validation) kurallarından geçirir, şüpheli alanları insan denetimine (human review) sunar ve onaylanmış sonucu yapılandırılmış bir çıktı olarak dışa aktarır.

Amaç, tam otomasyon değil; **güvenilir, ölçülebilir ve insan denetimiyle desteklenen** bir veri çıkarma akışıdır.

---

## 2. Hedef Kullanıcı

- **Birincil hedef kullanıcı:** Muhasebe ve ofis personeli. Faturaları işleyen, verileri doğrulayan ve onaylayan kişilerdir. Teknik uzmanlık gerektirmeyen, sade bir kullanım beklenir.
- **Gelecekteki ikincil kullanıcı:** Geliştirici veya şirket içi operasyon ekipleri. Çıkarılan yapılandırılmış veriyi başka sistemlerde kullanmak veya süreci ölçeklendirmek isteyen ekiplerdir. Bu kullanıcı grubu MVP kapsamında birincil öncelik değildir.

---

## 3. MVP Kullanıcı Akışı

Temel uçtan uca akış aşağıdaki adımlardan oluşur:

1. Kullanıcı **tek bir fatura** yükler.
2. Sistem faturadan **yapılandırılmış veri** çıkarır.
3. **Deterministik doğrulama (validation) kuralları** çalışır.
4. **Şüpheli alanlar**, insan denetimi (human review) ekranında gösterilir.
5. Kullanıcı alanları **düzeltir ve onaylar**.
6. Onaylanmış sonuç **JSON** olarak dışa aktarılır.

Bu akış tek kullanıcı ve tek belge için tasarlanmıştır ve baştan sona çalışması hedeflenir.

---

## 4. Desteklenen Belge Kapsamı (Sürümlü)

Belge kapsamı sürümlere ayrılmıştır. **V1.0, mevcut MVP kapsamıdır.** Sonraki sürümler ingestion (belge alımı) yeteneklerinin genişleme yönünü gösterir ve MVP'ye dahil değildir.

Tüm sürümlerde ortak sabitler: **Türkçe belgeler, TRY para birimi ve Türkiye'de kullanılan genel ticari faturalar.**

### V1.0 — Mevcut MVP kapsamı

- Türkçe
- TRY para birimi
- Türkiye'de kullanılan genel ticari faturalar
- Tek sayfalı veya kapsamı yönetilebilir dijital faturalar
- Metin katmanı bulunan dijital PDF
- Temel KDV yapıları

> **Not:** V1.0 kapsamında yalnızca **metin katmanı bulunan dijital PDF** desteklenir. **PNG, JPEG ve taranmış PDF desteği V1.0 kapsamı dışındadır** ve V1.1'e ertelenmiştir.

### V1.1 — MVP sonrası ingestion genişlemesi

- Temiz PNG ve JPEG belgeler
- Temiz taranmış PDF'ler
- OCR veya vision tabanlı ingestion

### V1.2 — Daha sonraki genişleme

- Eğri veya perspektifi bozulmuş fotoğraflar
- Gölgeli, bulanık veya düşük kaliteli belgeler
- Telefonla çekilmiş zor belge örnekleri

---

## 5. Güven (Confidence) ve Alan Yönlendirme (Flagging) Kararı

Bu projede, **LLM'in kendi ürettiği confidence skoru ana güven kaynağı olarak kullanılmayacaktır.** Bu tür skorlar, kalibre edilmiş bir doğruluk olasılığı ifade etmez.

MVP'de bir alanın insan denetimine (review) yönlendirilmesi, model tahminine değil, aşağıdaki **deterministik sinyallere** dayanacaktır:

- Validation kuralı ihlalleri
- Parse edilemeyen değerler
- Zorunlu alan eksikliği
- Format uyumsuzlukları
- Matematiksel tutarsızlıklar
- Alanlar arası çelişkiler
- Alan bazlı mantık kontrolleri

Başlangıçta üretilen değerler, gerçek bir doğruluk olasılığı olarak yorumlanamaz. Gerekirse bu değerler `review_required`, `risk_level`, `validation_severity` veya benzeri kavramlarla ifade edilebilir; ancak bunlar kalibre edilmiş bir olasılık değil, deterministik sinyallerin özetidir.

Gerçek olasılık anlamına gelen **kalibre edilmiş bir confidence skoru**, yeterli etiketli veri ve kullanıcı düzeltmesi oluşmadan kullanılmayacaktır.

---

## 6. MVP Başarı Hedefleri

Aşağıdaki hedefler, MVP için **yön gösterici (indicative)** başarı ölçütleridir. Bağlayıcı bir eşik veya garanti değil; geliştirmeyi yönlendiren birer **hedef / pusula** olarak kullanılır:

- **Temel alan doğruluğu:** yaklaşık %85 veya üzeri (hedef / pusula)
- **Sayısal alan doğruluğu:** yaklaşık %90 veya üzeri (hedef / pusula)
- **Geçerli JSON üretme oranı:** %95 veya üzeri
- **İşlem başarısızlık oranı:** %5 veya altında
- **Kritik doğrulama (validation) kuralları:** tamamı birim testli olmalı
- **Ölçüm:** belge başına maliyet ve latency (gecikme) ölçülmeli
- **Yönlendirme:** hatalı veya belirsiz alanlar insan denetimine (review) yönlendirilmeli

> Bu hedeflerin nasıl yorumlanması gerektiğine dair önemli uyarılar için "10. Ölçüm Hakkında Notlar" bölümüne bakınız.

---

## 7. MVP Dışı Konular

Aşağıdaki konular MVP kapsamı **dışındadır**:

- El yazısı belgeler
- Fiş, makbuz ve irsaliye
- PNG, JPEG ve taranmış PDF belgeler ile OCR/vision tabanlı ingestion (bkz. "4. Desteklenen Belge Kapsamı" — V1.1'e ertelendi)
- XML e-Fatura entegrasyonu
- Uluslararası dil, para birimi ve vergi sistemleri
- Toplu (batch) yükleme
- Çok kullanıcılı yapı
- ERP entegrasyonu

**MVP yaklaşımı:** Tek kullanıcı, tek belge; uçtan uca çalışan ve ölçülebilir bir sistem.

---

## 8. Gelecekteki Genişleme Alanları

Aşağıdaki alanlar MVP sonrası için olası genişleme yönleridir. MVP kapsamında ele alınmaz ve bu aşamada herhangi bir teknoloji veya mimari taahhüt oluşturmaz:

- Ek ingestion yetenekleri (PNG/JPEG, taranmış PDF, OCR/vision — sürümlü kapsam için bkz. "4. Desteklenen Belge Kapsamı")
- Ek belge türleri (fiş, makbuz, irsaliye vb.)
- XML e-Fatura entegrasyonu
- Uluslararası dil, para birimi ve vergi sistemleri desteği
- Toplu (batch) yükleme
- Çok kullanıcılı yapı ve yetkilendirme
- Kalibre edilmiş confidence skoru (yeterli etiketli veri ve kullanıcı düzeltmesi sonrası)
- ERP ve diğer kurumsal sistem entegrasyonları
- Geliştirici ve operasyon ekipleri için genişletilmiş kullanım senaryoları

---

## 9. Minimum Karmaşıklık İlkesi

Teknoloji ve repo kararlarında aşağıdaki ilke uygulanacaktır:

- Her teknoloji, mevcut bir MVP ihtiyacını çözmelidir.
- Daha basit bir alternatif yeterliyse, karmaşık çözüm seçilmemelidir.
- Gösterişli frontend, erken ölçekleme altyapısı ve varsayımsal gelecek ihtiyaçları, projenin çekirdeğinin önüne geçmemelidir.
- Review ekranının amacı görsel gösteriş değildir; belge ve çıkarılan alanların anlaşılır biçimde incelenip düzeltilmesidir.
- Extraction, validation, evaluation ve ölçüm, projenin temel mühendislik öncelikleridir.

---

## 10. Ölçüm Hakkında Notlar

Bu oranlar, küçük bir seed (başlangıç) veri seti üzerinde kullanılacak **yön gösterici MVP hedefleridir**. Kesin bir ürün güvencesi veya üretim seviyesi performans iddiası değildir. Kritik alanların tanımı ve nihai metrik hesaplama yöntemi, **extraction (veri çıkarma) şeması** aşamasında ayrıca belirlenecektir.

Ölçüm ve raporlamada aşağıdaki ilkeler uygulanır:

- 8–12 belgeli seed dataset sonuçları yalnızca **yön gösterici geliştirme ölçümleridir**.
- Bu sonuçlar, kanıtlanmış ürün performansı veya üretim seviyesi doğruluk iddiası olarak sunulmayacaktır.
- Evaluation raporlarında **belge sayısı** ve **toplam alan örneği sayısı** birlikte gösterilecektir.
- Her alan için **kaç örneğin değerlendirildiği** açıkça yazılacaktır.
- **Alan bazlı sonuçlar, hata kategorileri ve dataset sınırlılıkları** raporlanacaktır.
- Portföy anlatısında yalnızca doğruluk oranı değil, kullanılan **ölçüm metodolojisi** de açıklanacaktır.
