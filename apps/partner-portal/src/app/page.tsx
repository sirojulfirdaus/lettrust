// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD FR-02.01, §9.3.2; SA §11.3.1
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

// Menyediakan beranda portal simulasi dan akses langsung ke pemeriksaan surat.
export default function PortalHomePage() {
  return (
    <div className="space-y-8">
      <section className="space-y-3 py-6 sm:py-10">
        <p className="text-sm font-semibold uppercase tracking-wide text-primary">Portal Karier Mitra · Simulasi</p>
        <h1 className="max-w-2xl text-3xl font-bold tracking-tight sm:text-4xl">Periksa informasi pada surat penawaran kerja</h1>
        <p className="max-w-2xl text-muted-foreground">
          Gunakan kode referensi untuk memeriksa catatan penerbitan dan keutuhan berkas, atau minta analisis indikasi risiko pada isi PDF. Hasil pemeriksaan membantu Anda menentukan langkah selanjutnya dan bukan vonis.
        </p>
        <Button asChild size="lg"><Link href="/cek-offer-letter">Cek Offer Letter</Link></Button>
      </section>
      <section aria-label="Jenis pemeriksaan" className="grid gap-4 sm:grid-cols-3">
        {[
          ["Bukti penerbitan", "Memeriksa apakah kode referensi tercatat dan statusnya di registry."],
          ["Keutuhan berkas", "Membandingkan PDF dengan berkas yang dicatat untuk kode tersebut."],
          ["Indikasi risiko", "Menandai pola dalam isi surat untuk ditinjau lebih lanjut."],
        ].map(([title, description]) => (
          <Card key={title}>
            <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
            <CardContent><CardDescription>{description}</CardDescription></CardContent>
          </Card>
        ))}
      </section>
      <p className="text-xs text-muted-foreground">Portal demonstrasi ini menggunakan data sintetis. Didukung Lettrust.</p>
    </div>
  );
}
