// Owner: Van (PIC 2) | Status: STUB | Ref: PRD §9.2, §9.10, §9.11; SA §11.2.1
// TODO: Tampilkan menu sesuai role dari S-03 /auth/me (HR atau Admin) dan tombol Keluar; menyembunyikan menu tidak menggantikan otorisasi backend.
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { CONSOLE_ROUTES } from "@/lib/routes";

// Header Console dengan nama aplikasi, penanda data sintetis, dan navigasi placeholder.
export function ConsoleHeader() {
  const hrRoutes = CONSOLE_ROUTES.filter((r) => r.access === "hr" && !r.path.includes("["));
  const adminRoutes = CONSOLE_ROUTES.filter((r) => r.access === "admin" && !r.path.includes("["));
  return (
    <header className="border-b bg-card">
      <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center gap-4 px-4 py-3">
        <Link href="/" className="font-heading text-lg font-bold text-primary">
          Lettrust Console
        </Link>
        <Badge variant="outline">Data sintetis</Badge>
        <nav aria-label="Navigasi placeholder" className="ml-auto flex flex-wrap gap-4 text-sm">
          <span className="text-muted-foreground">Menu HR (placeholder):</span>
          {hrRoutes.map((r) => (
            <Link key={r.path} href={r.path} className="hover:underline">
              {r.title}
            </Link>
          ))}
          <span className="text-muted-foreground">Menu Admin (placeholder):</span>
          {adminRoutes.map((r) => (
            <Link key={r.path} href={r.path} className="hover:underline">
              {r.title}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
