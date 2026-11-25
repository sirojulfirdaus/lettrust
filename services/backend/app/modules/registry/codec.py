# Owner: Sat (PIC 6) | Status: COMPLETE | Ref: SA §6.3
"""Encoding identifier dan hash antara representasi API dan bytes32 on-chain."""

import re

_HEX64 = re.compile(r"[0-9a-fA-F]{64}")


# Mengubah proofId berprefiks 0x menjadi bytes32; menolak format lain sebelum RPC dijalankan.
def proof_id_to_bytes32(proof_id: str) -> bytes:
    if not isinstance(proof_id, str) or not proof_id.startswith("0x"):
        raise ValueError("proofId harus berformat 0x diikuti 64 karakter hex.")
    return hex64_to_bytes32(proof_id[2:])


# Mengubah hex 64 karakter (documentHash/issuerRef, tanpa 0x) menjadi 32 byte.
def hex64_to_bytes32(value: str) -> bytes:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise ValueError("Hash atau referensi penerbit harus berisi tepat 64 karakter hex tanpa prefiks.")
    return bytes.fromhex(value)


# Mengubah 32 byte menjadi hex 64 karakter lowercase tanpa 0x.
def bytes32_to_hex64(value: bytes) -> str:
    if not isinstance(value, bytes) or len(value) != 32:
        raise ValueError("Nilai on-chain harus berupa bytes dengan panjang tepat 32.")
    return value.hex()
