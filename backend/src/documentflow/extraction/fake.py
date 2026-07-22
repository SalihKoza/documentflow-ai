"""API anahtari ve ag gerektirmeyen extractor implementasyonlari.

Iki farkli ihtiyaci karsilar:

- `FakeExtractor`: onceden kurulmus bir sonucu dondurur. Cagiran kodu (pipeline,
  API katmani) her `ExtractionStatus` senaryosunda -- timeout, provider_error,
  refused -- surmek icindir.
- `RecordedExtractor`: kaydedilmis bir sagalayici YANIT METNINI `build_result`'tan
  gecirir. Gecersiz JSON, sema uyusmazligi ve parse dusurme davranislari boylece
  uretim yoluyla test edilir, taklit edilmez.

Ikisi de `ExtractorProtocol`'u yapisal olarak karsilar; mirasa gerek yoktur.
"""

from documentflow.extraction.mapping import build_result
from documentflow.extraction.types import (
    ExtractionRequest,
    ExtractionResult,
    ExtractionStatus,
    ProviderMetadata,
)


def fake_metadata(provider: str = "fake") -> ProviderMetadata:
    """Testler icin nötr metadata (gercek bir model/prompt surumu iddiasi yoktur)."""
    return ProviderMetadata(provider=provider, model="none", prompt_version="none")


class FakeExtractor:
    """Sabit bir sonuc dondurur ve aldigi istekleri kaydeder."""

    def __init__(self, result: ExtractionResult) -> None:
        self._result = result
        self.requests: list[ExtractionRequest] = []

    @classmethod
    def failing(
        cls,
        status: ExtractionStatus,
        *,
        error_detail: str | None = None,
        metadata: ProviderMetadata | None = None,
    ) -> "FakeExtractor":
        """Basarisiz bir sonuc dondururen fake (ornegin timeout senaryosu)."""
        if status is ExtractionStatus.ok:
            raise ValueError("failing() yalnizca basarisiz durumlar icindir")
        return cls(
            ExtractionResult(
                status=status,
                invoice=None,
                metadata=metadata or fake_metadata(),
                error_detail=error_detail,
            )
        )

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        self.requests.append(request)
        return self._result


class RecordedExtractor:
    """Kaydedilmis bir yanit metnini uretim cevrim yolundan gecirir."""

    def __init__(self, response_text: str, *, metadata: ProviderMetadata | None = None) -> None:
        self._response_text = response_text
        self._metadata = metadata or fake_metadata("recorded")
        self.requests: list[ExtractionRequest] = []

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        self.requests.append(request)
        return build_result(self._response_text, self._metadata)
