// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.04, §9.3.1, §9.5, §9.9.3; SA §10.5 (S-03), §10.6 (S-06)
"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle, Building2, FilePlus2, FileText, Loader2 } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { HrAuthorizationBadge, IssuerStatusBadge } from "@/components/issuers/issuer-status-badge";
import { ProofStatusBadge } from "@/components/proofs/proof-status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { MeResponse, ProofListResponse } from "@/lib/api/client";
import { loadHrHomeData, loadHrProofSummary } from "./hr-flow";
import {
  formatProofTimestamp,
  type HrStatusPresentation,
  type IssuerMembership,
} from "./hr-status";

type ProfileState =
  | { status: "loading" }
  | {
      status: "ready";
      profile: MeResponse;
      membership: IssuerMembership;
      hrStatus: HrStatusPresentation;
    }
  | { status: "error"; message: string };

type ProofSummaryState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; data: ProofListResponse }
  | { status: "error"; message: string };

// Halaman Beranda HR yang memuat status penerbit, otorisasi, dan ringkasan bukti dari backend.
export default function HrHomePage() {
  const router = useRouter();
  const [homeAttempt, setHomeAttempt] = useState(0);
  const [profileState, setProfileState] = useState<ProfileState>({ status: "loading" });
  const [proofState, setProofState] = useState<ProofSummaryState>({ status: "idle" });
  const proofRetryControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void loadHrHomeData({
      signal: controller.signal,
      onUnauthorized: () => router.replace("/login?reason=session_expired"),
      onProfileReady: (readyProfile) => {
        setProfileState({
          status: "ready",
          profile: readyProfile.profile,
          membership: readyProfile.membership,
          hrStatus: readyProfile.status,
        });
        setProofState({
          status: readyProfile.shouldLoadProofs ? "loading" : "idle",
        });
      },
    }).then((result) => {
      if (result.kind === "aborted" || result.kind === "unauthorized") {
        return;
      }
      if (result.kind === "redirect") {
        router.replace(result.to);
        return;
      }
      if (result.kind === "profile_error") {
        setProfileState({ status: "error", message: result.message });
        return;
      }
      if (result.proofsError !== null) {
        setProofState({ status: "error", message: result.proofsError });
      } else if (result.proofs !== null) {
        setProofState({ status: "ready", data: result.proofs });
      } else {
        setProofState({ status: "idle" });
      }
    });

    return () => {
      controller.abort();
      proofRetryControllerRef.current?.abort();
    };
  }, [homeAttempt, router]);

  // Memuat ulang data Beranda HR dari S-03 (dan S-06 bila berwenang).
  const handleRetryProfile = () => {
    proofRetryControllerRef.current?.abort();
    setProfileState({ status: "loading" });
    setProofState({ status: "idle" });
    setHomeAttempt((n) => n + 1);
  };

  // Memuat ulang ringkasan bukti penerbitan dari S-06 GET /api/v1/proofs tanpa memuat ulang kartu status.
  const handleRetryProofs = () => {
    proofRetryControllerRef.current?.abort();
    const controller = new AbortController();
    proofRetryControllerRef.current = controller;
    setProofState({ status: "loading" });

    void loadHrProofSummary({
      signal: controller.signal,
      onUnauthorized: () => router.replace("/login?reason=session_expired"),
    }).then((result) => {
      if (result.kind === "aborted" || result.kind === "unauthorized") {
        return;
      }
      if (result.kind === "error") {
        setProofState({ status: "error", message: result.message });
        return;
      }
      setProofState({ status: "ready", data: result.data });
    });
  };

  if (profileState.status === "loading") {
    return (
      <div
        role="status"
        aria-live="polite"
        className="mx-auto flex max-w-md flex-col items-center justify-center gap-3 py-16 text-center"
      >
        <Loader2 className="size-6 animate-spin text-primary" aria-hidden="true" />
        <p className="text-sm text-muted-foreground">Memuat status perusahaan dan otorisasi...</p>
      </div>
    );
  }

  if (profileState.status === "error") {
    return (
      <div className="mx-auto max-w-lg space-y-4 py-8">
        <Alert variant="destructive">
          <AlertCircle className="size-4" aria-hidden="true" />
          <AlertTitle>Gagal memuat Beranda HR</AlertTitle>
          <AlertDescription>{profileState.message}</AlertDescription>
        </Alert>
        <div className="flex flex-wrap gap-3">
          <Button type="button" onClick={handleRetryProfile} className="cursor-pointer">
            Coba lagi
          </Button>
          <Button asChild variant="outline" className="cursor-pointer">
            <Link href="/login">Ke halaman Masuk</Link>
          </Button>
        </div>
      </div>
    );
  }

  const { profile, membership, hrStatus: status } = profileState;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Beranda HR</h1>
          <p className="text-sm text-muted-foreground">
            Masuk sebagai <span className="font-medium text-foreground">{profile.displayName}</span>{" "}
            ({profile.email})
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {status.canIssueProof ? (
            <>
              <Button asChild size="lg" className="cursor-pointer">
                <Link href="/hr/proofs/new">
                  <FilePlus2 className="size-4" aria-hidden="true" />
                  Terbitkan Bukti
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg" className="cursor-pointer">
                <Link href="/hr/proofs">
                  <FileText className="size-4" aria-hidden="true" />
                  Lihat Daftar Bukti
                </Link>
              </Button>
            </>
          ) : (
            <Button
              type="button"
              size="lg"
              disabled
              aria-describedby="issue-disabled-reason"
              className="cursor-not-allowed"
            >
              <FilePlus2 className="size-4" aria-hidden="true" />
              Terbitkan Bukti
            </Button>
          )}
        </div>
      </div>

      <Card>
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-1">
              <CardTitle className="flex items-center gap-2 text-lg">
                <Building2 className="size-5 text-primary" aria-hidden="true" />
                <span>{membership.companyName}</span>
              </CardTitle>
              <CardDescription>
                ID Penerbit:{" "}
                <span className="font-mono text-xs font-medium text-foreground">
                  {membership.issuerId}
                </span>
              </CardDescription>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span>Penerbit:</span>
                <IssuerStatusBadge status={membership.issuerStatus} />
              </div>
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span>Otorisasi HR:</span>
                <HrAuthorizationBadge
                  status={membership.authorizationStatus}
                  issuerStatus={membership.issuerStatus}
                />
              </div>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="space-y-1">
            <h2 className="text-base font-semibold text-foreground">{status.summaryTitle}</h2>
            <p className="text-sm text-muted-foreground">{status.summaryDescription}</p>
          </div>

          {status.disabledReason ? (
            <div
              id="issue-disabled-reason"
              className="rounded-lg border bg-muted/50 px-3.5 py-2.5 text-sm text-foreground"
            >
              {status.disabledReason}
            </div>
          ) : null}

          {status.reviewNote ? (
            <div className="rounded-lg border border-status-danger/30 bg-status-danger/5 px-4 py-3">
              <p className="text-xs font-semibold text-status-danger">
                Catatan Peninjauan Administrator
              </p>
              <p className="mt-1 text-sm whitespace-pre-wrap text-foreground">
                {status.reviewNote}
              </p>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {status.canIssueProof ? (
        <Card>
          <CardHeader className="border-b">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="space-y-1">
                <CardTitle>Ringkasan Bukti Penerbitan</CardTitle>
                <CardDescription>
                  Daftar ringkas hingga 5 bukti terbaru yang diterbitkan oleh perusahaan Anda.
                </CardDescription>
              </div>
              <div className="flex items-center gap-3">
                {proofState.status === "ready" ? (
                  <span className="text-xs text-muted-foreground">Total: {proofState.data.total}</span>
                ) : null}
                <Button asChild variant="outline" size="sm" className="cursor-pointer">
                  <Link href="/hr/proofs">Lihat Daftar Bukti</Link>
                </Button>
              </div>
            </div>
          </CardHeader>

          <CardContent>
            {proofState.status === "loading" || proofState.status === "idle" ? (
              <div
                role="status"
                aria-live="polite"
                className="flex items-center gap-2.5 py-6 text-sm text-muted-foreground"
              >
                <Loader2 className="size-4 animate-spin text-primary" aria-hidden="true" />
                <span>Memuat ringkasan bukti...</span>
              </div>
            ) : proofState.status === "error" ? (
              <div className="space-y-3 py-2">
                <Alert variant="destructive">
                  <AlertCircle className="size-4" aria-hidden="true" />
                  <AlertTitle>Ringkasan bukti belum dapat dimuat</AlertTitle>
                  <AlertDescription>{proofState.message}</AlertDescription>
                </Alert>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleRetryProofs}
                  className="cursor-pointer"
                >
                  Coba lagi
                </Button>
              </div>
            ) : proofState.data.items.length === 0 ? (
              <div className="flex flex-col items-start justify-between gap-3 py-4 sm:flex-row sm:items-center">
                <p className="text-sm text-muted-foreground">Belum ada bukti penerbitan.</p>
                <Button asChild size="sm" className="cursor-pointer">
                  <Link href="/hr/proofs/new">
                    <FilePlus2 className="size-4" aria-hidden="true" />
                    Terbitkan Bukti Pertama
                  </Link>
                </Button>
              </div>
            ) : (
              <div className="divide-y">
                {proofState.data.items.map((item) => (
                  <div
                    key={item.proofId}
                    className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0 space-y-0.5">
                      <Link
                        href={`/hr/proofs/${encodeURIComponent(item.proofId)}`}
                        className="font-mono text-sm font-semibold text-primary underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                      >
                        {item.referenceCode}
                      </Link>
                      <p className="text-xs text-muted-foreground">
                        Diterbitkan: {formatProofTimestamp(item.issuedAt)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <ProofStatusBadge status={item.lifecycleStatus} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
