// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD §9.2, §9.9.1, §9.10; SA §11.2
import type { Metadata } from "next";
import { Inter, Plus_Jakarta_Sans } from "next/font/google";
import { ConsoleHeader } from "@/components/console-header";
import "./globals.css";

const inter = Inter({ variable: "--font-sans", subsets: ["latin"] });
const jakarta = Plus_Jakarta_Sans({ variable: "--font-heading", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Lettrust Console",
  description: "Lettrust Console untuk HR penerbit dan Administrator (prototipe, data sintetis).",
};

// Layout akar Console: font, token tema, dan header bersama.
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="id" className={`${inter.variable} ${jakarta.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <ConsoleHeader />
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
