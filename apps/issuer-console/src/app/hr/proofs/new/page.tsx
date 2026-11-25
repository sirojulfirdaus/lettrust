// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-03.01–FR-03.07, §9.8, §9.10; SA §10.6 (API-04), §11.2.3
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle, ArrowLeft, Loader2, ShieldAlert } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ProofResultCard } from "@/components/proofs/proof-result-card";
import { ProofUploadForm } from "@/components/proofs/proof-upload-form";
import type { IssueProofResponse, MeResponse } from "@/lib/api/client";
import { loadHrProofsGuard } from "../proofs-flow";

type GuardState =
  | { status: "loading" }
  | { status: "ready"; profile: MeResponse }
  | { status: "forbidden"; message: string }
  | { status: "error"; message: string };

// Halaman Penerbitan Bukti (API-04) dengan penjaga otorisasi HR dari S-03.
export default function IssueProofPage() {
  const router = useRouter();
  const [attempt, setAttempt] = useState(0);
  const [guardState, setGuardState] = useState<GuardState>({ status: "loading" });
  const [issuedProof, setIssuedProof] = useState<IssueProofResponse | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void loadHrProofsGuard({
      signal: controller.signal,
      onUnauthorized: () => router.replace("/login?reason=session_expired"),
    }).then((result) => {
      if (result.kind === "aborted" || result.kind === "unauthorized") {
        return;
      }
      if (result.kind === "redirect") {
        router.replace(result.to);
        return;
      }
      if (result.kind === "forbidden") {
        setGuardState({ status: "forbidden", message: result.message });
        return;
      }
      if (result.kind === "error") {
        setGuardState({ status: "error", message: result.message });
        return;
      }
      setGuardState({ status: "ready", profile: result.profile });
    });

    return () => {
      controller.abort();
    };
  }, [attempt, router]);

  if (guardState.status === "loading") {
    return (
      <div
        role="status"
        aria-live="polite"
        className="mx-auto flex max-w-md flex-col items-center justify-center gap-3 py-16 text-center"
      >
        <Loader2 className="size-6 animate-spin text-primary" aria-hidden="true" />
        <p className="text-sm text-muted-foreground">Memeriksa izin penerbitan bukti...</p>
      </div>
    );
  }

  if (guardState.status === "error") {
    return (
      <div className="mx-auto max-w-lg space-y-4 py-8">
        <Alert variant="destructive">
          <AlertCircle className="size-4" aria-hidden="true" />
          <AlertTitle>Gagal memuat halaman penerbitan</AlertTitle>
          <AlertDescription>{guardState.message}</AlertDescription>
        </Alert>
        <div className="flex flex-wrap gap-3">
          <Button
            type="button"
            onClick={() => {
              setGuardState({ status: "loading" });
              setAttempt((n) => n + 1);
            }}
            className="cursor-pointer"
          >
            Coba lagi
          </Button>
          <Button asChild variant="outline" className="cursor-pointer">
            <Link href="/hr">Kembali ke Beranda HR</Link>
          </Button>
        </div>
      </div>
    );
  }

  if (guardState.status === "forbidden") {
    return (
      <div className="mx-auto max-w-lg space-y-4 py-8">
        <Alert variant="destructive">
          <ShieldAlert className="size-4" aria-hidden="true" />
          <AlertTitle>Penerbitan bukti belum diizinkan</AlertTitle>
          <AlertDescription>{guardState.message}</AlertDescription>
        </Alert>
        <Button asChild variant="outline" className="cursor-pointer">
          <Link href="/hr">Kembali ke Beranda HR</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Terbitkan Bukti</h1>
          <p className="text-sm text-muted-foreground">
            Penerbit:{" "}
            <span className="font-medium text-foreground">
              {guardState.profile.membership?.companyName}
            </span>
          </p>
        </div>

        <Button asChild variant="outline" size="sm" className="cursor-pointer">
          <Link href="/hr/proofs">
            <ArrowLeft className="size-4" aria-hidden="true" />
            Daftar Bukti
          </Link>
        </Button>
      </div>

      {issuedProof ? (
        <ProofResultCard proof={issuedProof} onIssueAnother={() => setIssuedProof(null)} />
      ) : (
        <ProofUploadForm
          onIssued={(proof) => setIssuedProof(proof)}
          onUnauthorized={() => router.replace("/login?reason=session_expired")}
        />
      )}
    </div>
  );
}
