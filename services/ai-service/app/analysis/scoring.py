# Owner: B (PIC 5) | Status: COMPLETE | Ref: PRD §8.5, FR-05.06; SA §7.6
"""Skoring kategori risiko deterministik dari indikator tervalidasi."""

from app.analysis.taxonomy import TAXONOMY
from app.schemas import RiskCategory, Severity


# Menentukan kategori risiko dari himpunan kode indikator tervalidasi (BR-04.06); kode dihitung sekali.
def score(codes: set[str]) -> RiskCategory:
    if codes - TAXONOMY.keys():
        raise ValueError("Skoring hanya menerima kode dari taksonomi.")
    severities = [TAXONOMY[code].severity for code in codes]
    if Severity.HIGH in severities:
        return RiskCategory.HIGH
    if Severity.MEDIUM in severities or severities.count(Severity.LOW) >= 2:
        return RiskCategory.MEDIUM
    return RiskCategory.LOW
