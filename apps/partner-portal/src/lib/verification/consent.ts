// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD FR-02.06, BR-04.10, BR-05.04

// Mengembalikan teks persetujuan pemrosesan AI yang ditampilkan di samping kotak centang.
export function getAiConsentText(): string {
  return "Saya menyetujui pemrosesan AI atas isi surat ini. Teks surat akan diekstraksi dan dikirim ke penyedia model AI pihak ketiga untuk dianalisis. Berkas dan teks tidak disimpan oleh Lettrust. Hasil analisis bersifat indikatif.";
}
