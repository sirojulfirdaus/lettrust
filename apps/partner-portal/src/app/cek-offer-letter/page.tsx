// Owner: Pash (PIC 4) | Status: STUB | Ref: PRD FR-02.01–FR-02.11, §9.4–§9.8; SA §11.3
// TODO: Form dua mode, validasi berkas, persetujuan AI, status pemrosesan, hasil tiga panel, dan panduan; kirim hanya ke /api/verify.
import { PlaceholderPage } from "@/components/placeholder-page";
import { Badge } from "@/components/ui/badge";

// Halaman Cek Offer Letter (placeholder).
export default function CheckOfferLetterPage() {
  return (
    <PlaceholderPage
      title="Cek Offer Letter"
      owner="Pash (PIC 4)"
      refs={["PRD FR-02.01–FR-02.11", "PRD §9.4–§9.8", "SA §11.3"]}
      aside={<Badge variant="outline">Didukung Lettrust</Badge>}
      checklist={[
        "Penjelasan singkat: yang diperiksa (bukti penerbitan, keutuhan berkas, indikasi risiko) dan hasil bukan vonis keaslian/keamanan (FR-02.01/AC-04).",
        "Pilihan mode \"Saya punya kode referensi\" (awal) dan \"Saya tidak punya kode — analisis isi surat dengan AI\"; ganti mode menghapus input tidak relevan (FR-02.02).",
        "Mode Dengan Kode: kode wajib dengan contoh format, normalisasi; PDF opsional; opsi AI nonaktif tanpa berkas (FR-02.03).",
        "Mode Tanpa Kode: PDF wajib, AI selalu aktif, keterangan bukti dan keutuhan tidak diperiksa, saran meminta kode (FR-02.04).",
        "Validasi berkas: hanya PDF, ≤ 5 MB, tidak kosong; tampilkan nama dan ukuran; dapat dihapus/diganti (FR-02.05).",
        "Persetujuan AI tidak tercentang default, wajib bila AI dipilih, tidak diingat untuk pemeriksaan berikutnya (FR-02.06).",
        "Browser hanya POST multipart ke /api/verify milik portal (FR-02.07).",
        "Processing: indikator, tombol Periksa Surat nonaktif, info AI dapat memakan puluhan detik (FR-02.08).",
        "Tiga panel terpisah: Bukti Penerbitan & Status, Keutuhan Berkas, Indikasi Risiko (AI); label dan ikon sesuai §9.6, tidak hanya warna (FR-02.09).",
        "Panel Langkah yang Disarankan dari aturan G-01–G-10 §9.7 (FR-02.10).",
        "Error 400/413/415 sebagai pesan perbaikan §9.8; gangguan/timeout: \"Layanan pemeriksaan sedang tidak tersedia\"; input dipertahankan; tombol Periksa surat lain (FR-02.11).",
        "Tanpa label Asli/Palsu/Aman/Penipuan; seluruh teks API dirender sebagai teks biasa.",
      ]}
    />
  );
}
