"""Ham belge saklama: dosya sistemi + icerik adresli yol.

Karar: PDF baytlari dosya sisteminde tutulur; veritabani yalnizca metadata ve
GORECELI YOL saklar (PostgreSQL bytea degil). Gerekce:

- Gercek faturalar zaten `data/private/` altinda, `.gitignore` ile disli (D-029);
  ayni yerde durmalari gizlilik politikasiyla dogal olarak hizalanir.
- Belge baytlari veritabani yedeklerine ve dokumlerine girmez.
- Tek kullanici / tek belge olceginde bytea'nin sundugu tek gercek avantaj
  (transactional atomiklik) karsiliginda odenen bedel (yedek buyumesi, hassas
  icerigin dokumlere sizmasi) orantisizdir.

Yol ICERIK ADRESLIDIR (SHA-256): ayni belge iki kez yuklendiginde tek dosya kalir
ve yol tamamen onaltilik karakterlerden turedigi icin disaridan gelen bir ad
dizin agacinda gezinemez. Ayrica kanonik yol containment kontrolu yapilir.

Veritabani satiri ve migration BU ASAMADA URETILMEZ: onu tuketecek bir persistence
veya API katmani henuz yok; tuketicisi olmayan tablo D-012 ile celisir.
"""

import hashlib
import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict

# Icerik adresli yolun ilk seviyesi: tek dizinde on binlerce dosya birikmesin.
_SHARD_LENGTH = 2


class StoredDocument(BaseModel):
    """Saklanmis bir belgeye ait metadata (belge baytlarini ICERMEZ)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sha256: str
    # Saklama kokune GORE yol; mutlak yol tasinabilirligi bozar ve makine
    # bilgisini kayitlara sizdirir.
    relative_path: str
    size_bytes: int


def content_path(sha256: str, *, suffix: str = ".pdf") -> str:
    """Bir icerik hash'i icin goreli saklama yolunu uretir (saf)."""
    return f"{sha256[:_SHARD_LENGTH]}/{sha256}{suffix}"


def store_document(data: bytes, *, root: Path, suffix: str = ".pdf") -> StoredDocument:
    """Belgeyi icerik adresli yola atomik olarak yazar.

    Ayni icerik tekrar verilirse dosya yeniden yazilmaz; sonuc yine ayni metadata
    olur (idempotent). Yazim once gecici bir dosyaya yapilir ve `os.replace` ile
    yerine tasinir; boylece yarim yazilmis bir dosya hicbir zaman gorunmez.
    """
    digest = hashlib.sha256(data).hexdigest()
    relative = content_path(digest, suffix=suffix)

    resolved_root = root.resolve()
    # Kok BILINCLI olarak otomatik olusturulmaz: yapilandirmadaki bir yazim hatasi
    # sessizce yeni bir agac acip belgeleri beklenmedik bir yere dagitmamalidir.
    if not resolved_root.is_dir():
        raise FileNotFoundError(f"saklama koku bulunamadi: {root}")

    target = (resolved_root / relative).resolve()
    if not target.is_relative_to(resolved_root):
        raise ValueError("hedef yol saklama kokunun disina cikiyor")

    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.parent / f".{digest}.{os.getpid()}.tmp"
        temporary.write_bytes(data)
        os.replace(temporary, target)

    return StoredDocument(sha256=digest, relative_path=relative, size_bytes=len(data))
