// Owner: Van (PIC 2) | Status: STUB | Ref: PRD FR-03.01–FR-03.07, §9.8, §9.10; SA §10.6 (API-04), §11.2.3
// TODO: Unggah PDF final dengan konfirmasi, Idempotency-Key per upaya, proses API-04, tampilkan hasil penerbitan dan error §9.8.
import { PlaceholderPage } from "@/components/placeholder-page";

// Halaman Terbitkan Bukti (placeholder).
export default function IssueProofPage() {
  return (
    <PlaceholderPage
      title="Terbitkan Bukti"
      owner="Van (PIC 2)"
      refs={["PRD FR-03.01–FR-03.07", "PRD §9.8", "PRD §9.10", "SA §10.6 API-04", "SA §11.2.3"]}
      checklist={[
        "Unggah satu berkas PDF; validasi cepat di client (PDF, ≤ 5 MB, tidak kosong); backend tetap memvalidasi.",
        "Idempotency-Key baru (crypto.randomUUID()) saat berkas dipilih; Coba lagi memakai kunci yang sama; berkas lain membuat kunci baru.",
        "Dialog Confirmation: berkas adalah versi final dan perubahan apa pun terdeteksi sebagai berkas berbeda (FR-03.01/AC-03).",
        "API-04 POST /api/v1/proofs (multipart); state Processing dengan tombol nonaktif.",
        "Hasil: referenceCode (tombol salin), proofId, documentHash, ACTIVE, issuedAt, transaction.hash, transaction.blockNumber.",
        "Instruksi mengirim berkas yang sama persis beserta kode melalui kanal perusahaan (FR-03.07/AC-03).",
        "REGISTRY_UNAVAILABLE/REGISTRY_TRANSACTION_FAILED: pesan §9.8 tanpa menampilkan kode; tombol Coba lagi.",
        "IDEMPOTENCY_KEY_CONFLICT, DUPLICATE_ACTIVE_DOCUMENT (P1), 400/413/415, 403 sesuai pesan §9.8.",
      ]}
    />
  );
}
