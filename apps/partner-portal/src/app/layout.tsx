// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD FR-02.01/AC-03, §9.2, §9.9.2, §9.10; SA §11.3
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import "./globals.css";

const inter = Inter({ variable: "--font-sans", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Portal Karier Mitra (Simulasi)",
  description: "Portal job simulasi untuk demonstrasi integrasi Lettrust (data sintetis).",
};

// Layout akar portal: identitas portal simulasi dan penanda data sintetis.
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="id" className={`${inter.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <header className="border-b bg-card">
          <div className="mx-auto flex w-full max-w-4xl flex-wrap items-center gap-3 px-4 py-3">
            <Link href="/" className="text-lg font-bold text-primary">
              Portal Karier Mitra
            </Link>
            <Badge>Simulasi</Badge>
            <Badge variant="outline" className="ml-auto">
              Data sintetis
            </Badge>
          </div>
        </header>
        <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
