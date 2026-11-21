# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §6.3, §6.3.1
"""Pembuatan identifier acak (Crockford Base32) serta normalisasi dan validasi referenceCode."""

import hashlib
import re
import secrets

CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
REFERENCE_CODE_PATTERN = re.compile(r"^LTR-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$")
_CROCKFORD_DECODE = str.maketrans({"O": "0", "I": "1", "L": "1"})


class InvalidReferenceCodeError(ValueError):
    """Kode referensi tidak lolos format setelah normalisasi (INVALID_REFERENCE_CODE_FORMAT)."""


# Menghasilkan string acak sepanjang `length` dari alfabet Crockford Base32.
def random_crockford(length: int) -> str:
    return "".join(secrets.choice(CROCKFORD_ALPHABET) for _ in range(length))


# Membuat userId/hrId `USR-XXXXXXXX`.
def new_user_id() -> str:
    return f"USR-{random_crockford(8)}"


# Membuat issuerId `ISS-XXXXXXXX`.
def new_issuer_id() -> str:
    return f"ISS-{random_crockford(8)}"


# Membuat id partner `PRT-XXXXXXXX`.
def new_partner_id() -> str:
    return f"PRT-{random_crockford(8)}"


# Membuat verificationId `VER-XXXXXXXXXX`.
def new_verification_id() -> str:
    return f"VER-{random_crockford(10)}"


# Membuat requestId `req_` + 16 karakter acak.
def new_request_id() -> str:
    return f"req_{random_crockford(16)}"


# Membuat proofId `0x` + 64 hex lowercase dari 32 byte acak.
def new_proof_id() -> str:
    return "0x" + secrets.token_bytes(32).hex()


# Membuat referenceCode `LTR-XXXX-XXXX-XXXX` (60 bit acak); keunikan diperiksa pemanggil di basis data.
def new_reference_code() -> str:
    body = random_crockford(12)
    return f"LTR-{body[0:4]}-{body[4:8]}-{body[8:12]}"


# Menghitung issuerRef opaque: SHA-256 dari `lettrust:issuer:{issuerId}` (64 hex tanpa 0x).
def compute_issuer_ref(issuer_id: str) -> str:
    return hashlib.sha256(f"lettrust:issuer:{issuer_id}".encode()).hexdigest()


# Menormalisasi referenceCode sesuai SA §6.3.1; None bila kosong/spasi, raise bila format tidak valid.
def normalize_reference_code(raw: str | None) -> str | None:
    if raw is None or not raw.strip():
        return None
    compact = raw.strip().upper().replace(" ", "").replace("-", "")
    if compact.startswith("LTR"):
        compact = compact[3:]
    compact = compact.translate(_CROCKFORD_DECODE)
    candidate = f"LTR-{compact[0:4]}-{compact[4:8]}-{compact[8:12]}" if len(compact) == 12 else ""
    if not REFERENCE_CODE_PATTERN.fullmatch(candidate):
        raise InvalidReferenceCodeError("referenceCode tidak sesuai format LTR-XXXX-XXXX-XXXX")
    return candidate


# Memeriksa apakah string sudah berupa referenceCode ternormalisasi yang valid.
def is_valid_reference_code(value: str) -> bool:
    return REFERENCE_CODE_PATTERN.fullmatch(value) is not None
