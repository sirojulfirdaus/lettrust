# Owner: Sat (PIC 6) | Status: COMPLETE | Ref: SA §6.3; T6-02
"""Menguji batas format identifier dan hash sebelum data dikirim ke registry."""

from typing import Any

import pytest
from hexbytes import HexBytes

from app.modules.registry.codec import bytes32_to_hex64, hex64_to_bytes32, proof_id_to_bytes32


# Memastikan hex dengan huruf besar maupun kecil menghasilkan bytes32 yang sama tanpa mengubah urutan byte.
@pytest.mark.parametrize("value", ["00" * 32, "ab" * 32, "AB" * 32, "0123456789abcdef" * 4])
def test_hex_and_proof_id_decode_the_same_bytes(value: str) -> None:
    expected = bytes.fromhex(value)
    assert hex64_to_bytes32(value) == expected
    assert proof_id_to_bytes32("0x" + value) == expected
    assert bytes32_to_hex64(expected) == value.lower()


# Menolak proofId tanpa prefiks yang tepat, panjang salah, spasi, dan nilai non-hex.
@pytest.mark.parametrize(
    "value",
    [
        "",
        "ab" * 32,
        "0X" + "ab" * 32,
        "0x" + "ab" * 31,
        "0x" + "ab" * 33,
        "0x" + "gg" * 32,
        " 0x" + "ab" * 32,
        "0x" + "ab" * 32 + "\n",
        "0x" + "a " * 32,
        None,
        32,
        b"ab" * 32,
    ],
)
def test_proof_id_rejects_invalid_input(value: Any) -> None:
    with pytest.raises(ValueError):
        proof_id_to_bytes32(value)


# Menolak hash yang berprefiks, panjangnya bukan 64, mengandung spasi, atau bukan string hex.
@pytest.mark.parametrize(
    "value",
    ["", "0x" + "ab" * 32, "ab" * 31, "ab" * 33, "gg" * 32, "a " * 32, "ab" * 32 + "\n", None, 32, b"ab" * 32],
)
def test_hash_rejects_invalid_input(value: Any) -> None:
    with pytest.raises(ValueError):
        hex64_to_bytes32(value)


# Menerima bytes dan HexBytes dari web3, lalu menghasilkan hex lowercase tanpa prefiks.
@pytest.mark.parametrize("value", [bytes.fromhex("ab" * 32), HexBytes("0x" + "ab" * 32)])
def test_bytes32_returns_canonical_hex(value: bytes) -> None:
    assert bytes32_to_hex64(value) == "ab" * 32


# Menolak nilai on-chain dengan tipe atau panjang yang tidak sesuai bytes32.
@pytest.mark.parametrize("value", [b"", b"a" * 31, b"a" * 33, "ab" * 32, None, 32, bytearray(32)])
def test_bytes32_rejects_invalid_input(value: Any) -> None:
    with pytest.raises(ValueError):
        bytes32_to_hex64(value)
