# Dokumentasi Pengujian

Owner: Pash (PIC 4, koordinasi) · Status: COMPLETE · Ref: PRD §12.4–§12.6; SA §18

| Berkas | Isi |
| ----- | ----- |
| `test-cases.md` | Test case `TC-xxx` per skenario SCN-01–SCN-22 (kolom PRD §12.5) |
| `evidence/<TC-ID>/` | Bukti eksekusi: respons JSON, screenshot, log, referensi transaksi, identitas model |

Aturan:

1. Definisi kasus boleh ditulis sebelum pengujian; `Actual result` dan `Status` diisi setelah eksekusi nyata. Jangan pre-fill PASS.
2. Bukti skenario dan evaluasi berasal dari stack nyata (Anvil + LLM nyata). Hasil mock bukan bukti.
3. Bukti tidak memuat secret, token, atau kunci (`.env`, token partner/internal, JWT, kunci signer, API key LLM).
4. Bukti integrasi mencantumkan referensi transaksi registry; bukti AI mencantumkan model ID.
5. Test case yang gagal tetap dilaporkan beserta analisis dan tindak lanjut.

Skrip skenario API berada di [`scripts/scn/`](../../scripts/scn/README.md); skenario antarmuka (SCN-01, 03, 06, 08, 09, 13, 19) dieksekusi manual. Bagian per skenario mengikuti pembagian pelaksana di PLAN.md §7.1.
