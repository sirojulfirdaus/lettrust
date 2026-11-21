# Owner: Sat (PIC 6) | Status: STUB | Ref: SA §6.3
# TODO: Konversi representasi API (0x+64 hex / 64 hex) ke bytes32 dan sebaliknya, dengan validasi panjang.
"""Encoding identifier dan hash antara representasi API dan bytes32 on-chain."""


# Mengubah proofId `0x` + 64 hex menjadi 32 byte.
def proof_id_to_bytes32(proof_id: str) -> bytes:
    raise NotImplementedError("codec.proof_id_to_bytes32 belum diimplementasikan")


# Mengubah hex 64 karakter (documentHash/issuerRef, tanpa 0x) menjadi 32 byte.
def hex64_to_bytes32(value: str) -> bytes:
    raise NotImplementedError("codec.hex64_to_bytes32 belum diimplementasikan")


# Mengubah 32 byte menjadi hex 64 karakter lowercase tanpa 0x.
def bytes32_to_hex64(value: bytes) -> str:
    raise NotImplementedError("codec.bytes32_to_hex64 belum diimplementasikan")
