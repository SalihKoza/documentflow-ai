"""Test icin minimal PDF uretici (saf stdlib + pypdf).

Ikili test dosyasi repoya konmaz: fixture'lar kodda uretilir, boylece ne uretildigi
gorunur ve gozden gecirilebilir kalir. Uretilen PDF'ler gercek bir belgeden
turetilmemistir; icerikleri tamamen sentetiktir.
"""

from io import BytesIO

from pypdf import PdfReader, PdfWriter

_HEADER = b"%PDF-1.4\n"
# xref girdileri tam olarak 20 bayttir: 10 hane offset + bosluk + 5 hane surum +
# bosluk + tur harfi + bosluk + satir sonu.
_FREE_ENTRY = b"0000000000 65535 f \n"


def _assemble(objects: list[bytes]) -> bytes:
    """Nesneleri dogru xref offset'leriyle bir PDF govdesine dizer."""
    out = bytearray(_HEADER)
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode("ascii") + body + b"\nendobj\n"

    xref_offset = len(out)
    size = len(objects) + 1
    out += f"xref\n0 {size}\n".encode("ascii") + _FREE_ENTRY
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode("ascii")
    out += (f"trailer\n<< /Size {size} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n").encode(
        "ascii"
    )
    return bytes(out)


def _stream_object(payload: bytes) -> bytes:
    return (
        b"<< /Length "
        + str(len(payload)).encode("ascii")
        + b" >>\nstream\n"
        + payload
        + b"endstream"
    )


def _page_objects(content: bytes) -> list[bytes]:
    return [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        _stream_object(content),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]


def text_layer_pdf(text: str = "Fatura No ABC2025000000123 Genel Toplam 3.600,00 TL") -> bytes:
    """Cikarilabilir metin katmani olan tek sayfali PDF."""
    payload = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET\n".encode("ascii")
    return _assemble(_page_objects(payload))


def image_only_pdf() -> bytes:
    """Metin katmani olmayan PDF (taranmis belgeyi temsil eder): yalnizca cizim."""
    payload = b"0 0 0 RG 4 w 72 72 468 648 re S\n"
    return _assemble(_page_objects(payload))


def encrypted_pdf(password: str = "sentetik-parola") -> bytes:
    """Sifreli PDF (pypdf'in kendi sifreleme yolu ile uretilir)."""
    writer = PdfWriter()
    writer.append_pages_from_reader(PdfReader(BytesIO(text_layer_pdf())))
    writer.encrypt(password)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def corrupt_pdf() -> bytes:
    """PDF imzasi tasiyan fakat ayristirilamayan govde."""
    return _HEADER + b"bu bir PDF govdesi degil\n"
