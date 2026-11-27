// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD FR-02.01–FR-02.11, §9.4–§9.8; SA §11.3
import { VerifyForm } from "@/components/verification/verify-form";
import { readMaxUploadBytes } from "@/lib/server/config";

// Dirender per permintaan agar MAX_UPLOAD_BYTES dibaca saat runtime, bukan saat next build.
export const dynamic = "force-dynamic";

// Menyediakan halaman pemeriksaan tanpa login; hanya angka batas unggah yang dikirim ke browser, bukan token.
export default function CheckOfferLetterPage() {
  const maxUploadBytes = readMaxUploadBytes();
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Cek Offer Letter</h1>
        <p className="mt-1 text-xs text-muted-foreground">Didukung Lettrust</p>
      </div>
      <p className="max-w-3xl text-muted-foreground">
        Periksa bukti penerbitan, keutuhan berkas, dan indikasi risiko pada isi surat secara terpisah. Hasil ini bersifat informatif dan bukan vonis; konfirmasikan penawaran melalui kanal resmi perusahaan.
      </p>
      <VerifyForm maxUploadBytes={maxUploadBytes} />
    </div>
  );
}
