"""Extraction sagalayici arayuzu.

`typing.Protocol` bilincli olarak ABC yerine kullanilir: adapter'lar bir taban
siniftan TUREMEK ZORUNDA DEGILDIR, yalnizca imzayi karsilamalari yeterlidir
(yapisal tipleme). Bu, sagalayici paketlerinin domain'e bagimli olmasini onler ve
test sahtelerini (fake) mirassiz yazilabilir kilar.
"""

from typing import Protocol, runtime_checkable

from documentflow.extraction.types import ExtractionRequest, ExtractionResult


@runtime_checkable
class ExtractorProtocol(Protocol):
    """Bir belgeden yapilandirilmis fatura verisi cikaran bilesen.

    Sozlesme:
      - Sagalayici hatalari ISTISNA OLARAK DISARI SIZMAZ; `ExtractionResult`
        icindeki `status` degerine cevrilir (timeout, provider_error, refused...).
      - Basarisiz sonucta `invoice` None'dir.
      - Cagri saf olmak zorunda degildir (ag erisimi normaldir), fakat girdiyi
        degistirmez.
    """

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        """Belgeden cikarim yapar ve her durumda bir sonuc dondurur."""
        ...
