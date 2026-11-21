# Owner: B (PIC 5) | Status: STUB | Ref: PRD §8.5, FR-05.06; SA §7.6
# TODO: HIGH bila ada indikator HIGH; MEDIUM bila ada MEDIUM atau minimal 2 LOW berbeda; selain itu LOW.
"""Skoring kategori risiko deterministik dari indikator tervalidasi."""

from app.schemas import RiskCategory


# Menentukan kategori risiko dari himpunan kode indikator tervalidasi (BR-04.06); kode dihitung sekali.
def score(codes: set[str]) -> RiskCategory:
    raise NotImplementedError("scoring.score belum diimplementasikan")
