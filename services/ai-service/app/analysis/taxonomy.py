# Owner: B (PIC 5) | Status: COMPLETE | Ref: PRD §8.4, §9.6.3; SA §7.6, AD-09
"""Taksonomi tertutup indikator risiko; satu-satunya definisi kode, label, dan tingkat (PRD §8.4)."""

from dataclasses import dataclass

from app.schemas import Severity


@dataclass(frozen=True)
class Indicator:
    """Definisi satu kode indikator beserta contoh untuk prompt dan baseline."""

    code: str
    label: str
    severity: Severity
    definition: str
    positive_examples: tuple[str, ...]
    negative_examples: tuple[str, ...] = ()


TAXONOMY: dict[str, Indicator] = {
    indicator.code: indicator
    for indicator in (
        Indicator(
            code="PAYMENT_REQUEST",
            label="Permintaan pembayaran kepada pelamar",
            severity=Severity.HIGH,
            definition="Pelamar diminta membayar sejumlah uang sebelum mulai bekerja.",
            positive_examples=(
                "Biaya administrasi, pelatihan, seragam, medical check-up, tiket, akomodasi, atau deposit yang "
                "dibayarkan pelamar sebelum bekerja.",
            ),
            negative_examples=(
                "Biaya yang ditanggung atau dibayar perusahaan (misalnya biaya relokasi dibayar perusahaan) "
                "bukan PAYMENT_REQUEST.",
            ),
        ),
        Indicator(
            code="SENSITIVE_DATA_REQUEST",
            label="Permintaan data atau akses sensitif",
            severity=Severity.HIGH,
            definition="Pelamar diminta memberikan data rahasia atau akses ke rekening/akun.",
            positive_examples=("OTP, PIN, password, foto kartu ATM, akses rekening, atau data kartu kredit.",),
        ),
        Indicator(
            code="UNOFFICIAL_CONTACT",
            label="Kontak melalui kanal tidak resmi",
            severity=Severity.MEDIUM,
            definition="Komunikasi hanya diarahkan ke kanal pribadi yang mengatasnamakan HR perusahaan.",
            positive_examples=(
                "Komunikasi hanya melalui nomor pesan pribadi atau email layanan gratis yang mengatasnamakan HR.",
            ),
        ),
        Indicator(
            code="URGENCY_PRESSURE",
            label="Tekanan waktu atau ancaman",
            severity=Severity.MEDIUM,
            definition="Pelamar ditekan untuk segera bertindak atau diancam kehilangan posisi.",
            positive_examples=("Tenggat konfirmasi sangat singkat, ancaman kehilangan posisi, kuota terbatas.",),
        ),
        Indicator(
            code="IDENTITY_INCONSISTENCY",
            label="Informasi perusahaan atau penawaran tidak konsisten",
            severity=Severity.MEDIUM,
            definition="Identitas perusahaan atau rincian penawaran saling bertentangan di dalam surat.",
            positive_examples=("Nama perusahaan, alamat, posisi, atau penanda tangan yang tidak saling konsisten.",),
        ),
        Indicator(
            code="UNREALISTIC_COMPENSATION",
            label="Kompensasi tidak wajar",
            severity=Severity.LOW,
            definition="Kompensasi jauh melebihi kewajaran untuk posisi yang disebutkan.",
            positive_examples=("Gaji atau fasilitas yang jauh melebihi kewajaran untuk posisi yang disebutkan.",),
        ),
        Indicator(
            code="VAGUE_JOB_DETAILS",
            label="Rincian pekerjaan tidak jelas",
            severity=Severity.LOW,
            definition="Surat tidak menjelaskan pekerjaan secara memadai.",
            positive_examples=("Tanpa rincian tanggung jawab, lokasi, atau atasan; salam tidak spesifik.",),
        ),
    )
}


# Mengembalikan definisi indikator untuk kode; KeyError untuk kode di luar taksonomi.
def get_indicator(code: str) -> Indicator:
    return TAXONOMY[code]
