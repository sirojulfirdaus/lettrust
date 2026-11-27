// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.02/AC-07; SA §11.2.1, §11.2.2
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle, Loader2 } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ApiError, fetchSessionProfile } from "@/lib/api/client";
import { resolveLandingRoute } from "@/lib/routes";
import { readSession, sessionRedirectPath } from "@/lib/session";

// Halaman akar Console: mengarahkan pengguna ke area yang sesuai berdasarkan sesi dan profil S-03.
export default function HomePage() {
  const router = useRouter();
  const [attempt, setAttempt] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const session = readSession();
    if (!session) {
      router.replace(sessionRedirectPath());
      return;
    }

    const controller = new AbortController();
    fetchSessionProfile({
      signal: controller.signal,
      onUnauthorized: () => router.replace("/login?reason=session_expired"),
    })
      .then((profile) => {
        if (!controller.signal.aborted) {
          router.replace(resolveLandingRoute(profile));
        }
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        if (error instanceof ApiError && error.status === 401) {
          return;
        }
        const message =
          error instanceof ApiError
            ? error.message
            : "Tidak dapat menghubungi layanan backend. Pastikan layanan aktif lalu coba lagi.";
        setErrorMessage(message);
      });

    return () => controller.abort();
  }, [attempt, router]);

  const handleRetry = () => {
    setErrorMessage(null);
    setAttempt((n) => n + 1);
  };

  if (!errorMessage) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="mx-auto flex max-w-md flex-col items-center justify-center gap-3 py-16 text-center"
      >
        <Loader2 className="size-6 animate-spin text-primary" aria-hidden="true" />
        <p className="text-sm text-muted-foreground">Memeriksa sesi Anda...</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg space-y-4 py-8">
      <Alert variant="destructive">
        <AlertCircle className="size-4" aria-hidden="true" />
        <AlertTitle>Gagal memuat sesi</AlertTitle>
        <AlertDescription>{errorMessage}</AlertDescription>
      </Alert>
      <div className="flex flex-wrap gap-3">
        <Button type="button" onClick={handleRetry} className="cursor-pointer">
          Coba lagi
        </Button>
        <Button asChild variant="outline">
          <Link href="/login">Ke halaman Masuk</Link>
        </Button>
      </div>
    </div>
  );
}
