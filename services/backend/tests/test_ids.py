# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §6.3, §6.3.1
"""Test pembuatan identifier dan normalisasi referenceCode."""

import re

import pytest

from app.core import ids

CROCKFORD = set(ids.CROCKFORD_ALPHABET)


# Setiap generator menghasilkan prefiks, panjang, dan alfabet sesuai SA §6.3.
@pytest.mark.parametrize(
    ("factory", "prefix", "length"),
    [
        (ids.new_user_id, "USR-", 8),
        (ids.new_issuer_id, "ISS-", 8),
        (ids.new_partner_id, "PRT-", 8),
        (ids.new_verification_id, "VER-", 10),
        (ids.new_request_id, "req_", 16),
    ],
)
def test_prefixed_ids(factory, prefix, length):
    value = factory()
    assert value.startswith(prefix)
    body = value[len(prefix) :]
    assert len(body) == length
    assert set(body) <= CROCKFORD


# Alfabet Crockford tidak memuat I, L, O, U.
def test_alphabet_excludes_ambiguous_letters():
    assert len(ids.CROCKFORD_ALPHABET) == 32
    assert not set("ILOU") & CROCKFORD


# proofId: 0x + 64 hex lowercase, acak.
def test_proof_id_format_and_randomness():
    values = {ids.new_proof_id() for _ in range(50)}
    assert len(values) == 50
    assert all(re.fullmatch(r"0x[0-9a-f]{64}", v) for v in values)


# referenceCode baru selalu valid dan unik pada sampel.
def test_reference_code_generation():
    values = {ids.new_reference_code() for _ in range(200)}
    assert len(values) == 200
    assert all(ids.is_valid_reference_code(v) for v in values)


# issuerRef deterministik: SHA-256 `lettrust:issuer:{issuerId}`.
def test_issuer_ref():
    ref = ids.compute_issuer_ref("ISS-4D8N2P6R")
    assert ref == ids.compute_issuer_ref("ISS-4D8N2P6R")
    assert re.fullmatch(r"[0-9a-f]{64}", ref)
    assert ref != ids.compute_issuer_ref("ISS-4D8N2P6S")


# Normalisasi: trim, kapital, spasi/tanda hubung, prefiks opsional, dekode O→0 dan I/L→1.
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("LTR-7K3M-9QX2-H4TD", "LTR-7K3M-9QX2-H4TD"),
        ("  ltr-7k3m-9qx2-h4td  ", "LTR-7K3M-9QX2-H4TD"),
        ("LTR 7K3M 9QX2 H4TD", "LTR-7K3M-9QX2-H4TD"),
        ("ltr7k3m9qx2h4td", "LTR-7K3M-9QX2-H4TD"),
        ("7K3M-9QX2-H4TD", "LTR-7K3M-9QX2-H4TD"),
        ("LTR-O0O0-1111-2222", "LTR-0000-1111-2222"),
        ("LTR-IL00-li00-oo00", "LTR-1100-1100-0000"),
        ("L T R - 7 K 3 M - 9 Q X 2 - H 4 T D", "LTR-7K3M-9QX2-H4TD"),
    ],
)
def test_normalize_valid(raw, expected):
    assert ids.normalize_reference_code(raw) == expected


# Kosong atau hanya spasi diperlakukan sebagai tidak ada.
@pytest.mark.parametrize("raw", [None, "", "   ", "\t\n"])
def test_normalize_absent(raw):
    assert ids.normalize_reference_code(raw) is None


# Input tidak valid menghasilkan InvalidReferenceCodeError.
@pytest.mark.parametrize(
    "raw",
    [
        "LTR-7K3M-9QX2",
        "LTR-7K3M-9QX2-H4TD-AAAA",
        "LTR-7K3M-9QX2-H4TU",
        "LTR-7K3M-9QX2-H4T!",
        "ABC-7K3M-9QX2-H4TD",
        "LTR",
        "LTR-",
        "7K3M9QX2H4T",
        "LTR_7K3M_9QX2_H4TD",
    ],
)
def test_normalize_invalid(raw):
    with pytest.raises(ids.InvalidReferenceCodeError):
        ids.normalize_reference_code(raw)
