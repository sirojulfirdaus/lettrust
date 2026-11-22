// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.04, §9.3.1, §9.5, §9.9.3; SA §10.5 (S-03), §10.6 (S-06)
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  Building2,
  CheckCircle2,
  Clock,
  FilePlus2,
  FileText,
  Loader2,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ApiError,
  apiFetch,
  fetchSessionProfile,
  type MeResponse,
  type ProofListResponse,
} from "@/lib/api/client";
import { canIssueProofs } from "@/lib/routes";
import { readSession } from "@/lib/session";
import {
  formatProofTimestamp,
  getHrStatusPresentation,
  getProofLifecyclePresentation,
  type StatusTone,
} from "./hr-status";

type ProfileState =
  | { status: "loading" }
  | { status: "ready"; profile: MeResponse }
  | { status: "error"; message: string };

type ProofSummaryState =
  | { status: "loading" }
  | { status: "ready"; data: ProofListResponse }
  | { status: "error"; message: string };

// Mengembalikan kelas warna badge berdasarkan nada status PRD §9.9.3.
function getToneClassName(tone: StatusTone): string {
  switch (tone) {
    case "positive":
      return "border-status-positive/30 bg-status-positive/10 text-status-positive";
    case "warning":
      return "border-status-warning/30 bg-status-warning/10 text-status-warning";
    case "danger":
      return "border-status-danger/30 bg-status-danger/10 text-status-danger";
    case "neutral":
      return "border-status-neutral/30 bg-status-neutral/10 text-status-neutral";
  }
}

// Menampilkan badge status dengan kombinasi warna, ikon, dan teks agar mudah dikenali.
function StatusBadge({ label, tone }: { label: string; tone: StatusTone }) {
  const Icon =
    tone === "positive"
      ? CheckCircle2
      : tone === "warning"
        ? Clock
        : tone === "danger"
          ? XCircle
          : ShieldAlert;

  return (
    <Badge variant="outline" className={`gap-1.5 px-2.5 py-0.5 ${getToneClassName(tone)}`}>
      <Icon className="size-3.5" aria-hidden="true" />
      <span>{label}</span>
    </Badge>
  );
}

// Halaman Beranda HR yang memuat status penerbit, otorisasi, dan ringkasan bukti dari backend.
export default function HrHomePage() {
  const router = useRouter();
  const [profileAttempt, setProfileAttempt] = useState(0);
  const [profileState, setProfileState] = useState<ProfileState>({ status: "loading" });

  const [proofAttempt, setProofAttempt] = useState(0);
  const [proofState, setProofState] = useState<ProofSummaryState>({ status: "loading" });

  useEffect(() => {
    const session = readSession();
    if (!session) {
      router.replace("/login");
      return;
    }

    const controller = new AbortController();
    fetchSessionProfile({
      signal: controller.signal,
      onUnauthorized: () => router.replace("/login?reason=session_expired"),
    })
      .then((profile) => {
        if (controller.signal.aborted) {
          return;
        }
        if (profile.role === "ADMIN") {
          router.replace("/admin/issuers");
          return;
        }
        if (profile.membership === null) {
          router.replace("/onboarding/company");
          return;
        }
        setProfileState({ status: "ready", profile });
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
        setProfileState({ status: "error", message });
      });

    return () => controller.abort();
  }, [profileAttempt, router]);

  const isAuthorizedIssuer =
    profileState.status === "ready" && canIssueProofs(profileState.profile);

  useEffect(() => {
    if (!isAuthorizedIssuer) {
      return;
    }

    const controller = new AbortController();
    apiFetch<ProofListResponse>("/api/v1/proofs", {
      method: "GET",
      query: { limit: 5, offset: 0 },
      signal: controller.signal,
      onUnauthorized: () => router.replace("/login?reason=session_expired"),
    })
      .then((data) => {
        if (!controller.signal.aborted) {
          setProofState({ status: "ready", data });
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
            : "Ringkasan bukti belum dapat dimuat. Coba lagi beberapa saat lagi.";
        setProofState({ status: "error", message });
      });

    return () => controller.abort();
  }, [isAuthorizedIssuer, proofAttempt, router]);

  // Memuat ulang data profil sesi dari S-03 GET /api/v1/auth/me.
  const handleRetryProfile = () => {
    setProfileState({ status: "loading" });
    setProfileAttempt((n) => n + 1);
  };

  // Memuat ulang ringkasan bukti penerbitan dari S-06 GET /api/v1/proofs.
  const handleRetryProofs = () => {
    setProofState({ status: "loading" });
    setProofAttempt((n) => n + 1);
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

  const { profile } = profileState;
  const membership = profile.membership;
  if (!membership) {
    return null;
  }

  const status = getHrStatusPresentation(membership);

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
                <StatusBadge label={status.issuerStatusLabel} tone={status.issuerTone} />
              </div>
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span>Otorisasi HR:</span>
                <StatusBadge label={status.authorizationLabel} tone={status.authorizationTone} />
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
                  <Badge variant="secondary">Total: {proofState.data.total}</Badge>
                ) : null}
                <Button asChild variant="outline" size="sm" className="cursor-pointer">
                  <Link href="/hr/proofs">Lihat Daftar Bukti</Link>
                </Button>
              </div>
            </div>
          </CardHeader>

          <CardContent>
            {proofState.status === "loading" ? (
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
                {proofState.data.items.map((item) => {
                  const lifecycle = getProofLifecyclePresentation(item.lifecycleStatus);
                  return (
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
                        <StatusBadge label={lifecycle.label} tone={lifecycle.tone} />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
