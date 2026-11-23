// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.05, FR-01.06, §9.8; SA §10.5 (S-05, API-02, API-03)
"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { AlertCircle, ArrowLeft, Building2, Loader2, ShieldAlert } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { HrAuthorizationPanel } from "@/components/issuers/hr-authorization-panel";
import {
  formatIssuerTimestamp,
  IssuerStatusBadge,
} from "@/components/issuers/issuer-status-badge";
import { VerificationDecisionDialog } from "@/components/issuers/verification-decision-dialog";
import type { IssuerDetailResponse } from "@/lib/api/client";
import { loadIssuerDetail } from "../admin-issuers-flow";

type DetailState =
  | { status: "loading" }
  | { status: "forbidden"; message: string }
  | { status: "not_found"; message: string }
  | { status: "error"; message: string }
  | { status: "ready"; data: IssuerDetailResponse };

// Halaman Detail Penerbit untuk Administrator (S-05) beserta verifikasi (API-02) dan otorisasi HR (API-03).
export default function IssuerDetailPage() {
  const params = useParams<{ issuerId: string }>();
  const router = useRouter();
  const rawIssuerId = params?.issuerId ?? "";
  const issuerId = decodeURIComponent(rawIssuerId);

  const [refreshCount, setRefreshCount] = useState(0);
  const [state, setState] = useState<DetailState>({ status: "loading" });

  useEffect(() => {
    if (!issuerId) {
      return;
    }

    const controller = new AbortController();
    void loadIssuerDetail({
      issuerId,
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
        setState({ status: "forbidden", message: result.message });
        return;
      }
      if (result.kind === "not_found") {
        setState({ status: "not_found", message: result.message });
        return;
      }
      if (result.kind === "error") {
        setState({ status: "error", message: result.message });
        return;
      }
      setState({ status: "ready", data: result.data });
    });

    return () => {
      controller.abort();
    };
  }, [issuerId, refreshCount, router]);

  const handleRefresh = useCallback(() => {
    setRefreshCount((n) => n + 1);
  }, []);

  if (!issuerId) {
    return (
      <div className="mx-auto max-w-lg space-y-4 py-8">
        <Alert variant="destructive">
          <AlertCircle className="size-4" aria-hidden="true" />
          <AlertTitle>Penerbit tidak ditemukan</AlertTitle>
          <AlertDescription>ID penerbit tidak valid.</AlertDescription>
        </Alert>
        <Button asChild variant="outline" className="cursor-pointer">
          <Link href="/admin/issuers">Kembali ke Daftar Penerbit</Link>
        </Button>
      </div>
    );
  }

  if (state.status === "loading") {
    return (
      <div
        role="status"
        aria-live="polite"
        className="mx-auto flex max-w-md flex-col items-center justify-center gap-3 py-16 text-center"
      >
        <Loader2 className="size-6 animate-spin text-primary" aria-hidden="true" />
        <p className="text-sm text-muted-foreground">Memuat detail penerbit...</p>
      </div>
    );
  }

  if (state.status === "forbidden") {
    return (
      <div className="mx-auto max-w-lg space-y-4 py-8">
        <Alert variant="destructive">
          <ShieldAlert className="size-4" aria-hidden="true" />
          <AlertTitle>Akses ditolak</AlertTitle>
          <AlertDescription>{state.message}</AlertDescription>
        </Alert>
        <Button asChild variant="outline" className="cursor-pointer">
          <Link href="/hr">Kembali ke Beranda HR</Link>
        </Button>
      </div>
    );
  }

  if (state.status === "not_found") {
    return (
      <div className="mx-auto max-w-lg space-y-4 py-8">
        <Alert variant="destructive">
          <AlertCircle className="size-4" aria-hidden="true" />
          <AlertTitle>Penerbit tidak ditemukan</AlertTitle>
          <AlertDescription>{state.message}</AlertDescription>
        </Alert>
        <Button asChild variant="outline" className="cursor-pointer">
          <Link href="/admin/issuers">Kembali ke Daftar Penerbit</Link>
        </Button>
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="mx-auto max-w-lg space-y-4 py-8">
        <Alert variant="destructive">
          <AlertCircle className="size-4" aria-hidden="true" />
          <AlertTitle>Gagal memuat detail penerbit</AlertTitle>
          <AlertDescription>{state.message}</AlertDescription>
        </Alert>
        <div className="flex flex-wrap gap-3">
          <Button
            type="button"
            onClick={() => {
              setState({ status: "loading" });
              handleRefresh();
            }}
            className="cursor-pointer"
          >
            Coba lagi
          </Button>
          <Button asChild variant="outline" className="cursor-pointer">
            <Link href="/admin/issuers">Kembali ke Daftar Penerbit</Link>
          </Button>
        </div>
      </div>
    );
  }

  const issuer = state.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button asChild variant="ghost" size="sm" className="cursor-pointer">
          <Link href="/admin/issuers">
            <ArrowLeft className="size-4" aria-hidden="true" />
            Kembali ke Daftar Penerbit
          </Link>
        </Button>
      </div>

      <Card>
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-1">
              <CardTitle className="flex items-center gap-2 text-xl">
                <Building2 className="size-5 text-primary" aria-hidden="true" />
                <span>{issuer.companyName}</span>
              </CardTitle>
              <CardDescription>
                ID Penerbit:{" "}
                <span className="font-mono text-xs font-medium text-foreground">
                  {issuer.issuerId}
                </span>
              </CardDescription>
            </div>
            <IssuerStatusBadge status={issuer.issuerStatus} />
          </div>
        </CardHeader>

        <CardContent className="grid gap-4 pt-6 sm:grid-cols-2">
          <div>
            <p className="text-xs text-muted-foreground">Nomor Registrasi</p>
            <p className="mt-0.5 font-mono text-sm font-medium text-foreground">
              {issuer.registrationNumber}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Email Kontak Perusahaan</p>
            <p className="mt-0.5 text-sm font-medium text-foreground">{issuer.contactEmail}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Waktu Pengajuan</p>
            <p className="mt-0.5 text-sm text-foreground">
              {formatIssuerTimestamp(issuer.createdAt)}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Referensi Bukti</p>
            <p className="mt-0.5 font-mono text-sm text-foreground">{issuer.evidenceRef ?? "-"}</p>
          </div>

          {issuer.reviewedAt ? (
            <>
              <div>
                <p className="text-xs text-muted-foreground">Ditinjau Oleh</p>
                <p className="mt-0.5 font-mono text-sm text-foreground">
                  {issuer.reviewedBy ?? "-"}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Waktu Peninjauan</p>
                <p className="mt-0.5 text-sm text-foreground">
                  {formatIssuerTimestamp(issuer.reviewedAt)}
                </p>
              </div>
            </>
          ) : null}

          {issuer.reviewNote ? (
            <div className="sm:col-span-2">
              <p className="text-xs text-muted-foreground">Catatan Peninjauan</p>
              <p className="mt-1 rounded-md border bg-muted/40 px-3 py-2 text-sm whitespace-pre-wrap text-foreground">
                {issuer.reviewNote}
              </p>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {issuer.issuerStatus === "PENDING" ? (
        <VerificationDecisionDialog
          issuerId={issuer.issuerId}
          companyName={issuer.companyName}
          onSuccess={handleRefresh}
        />
      ) : null}

      <HrAuthorizationPanel
        issuerId={issuer.issuerId}
        issuerStatus={issuer.issuerStatus}
        members={issuer.members}
        onAuthorized={handleRefresh}
      />
    </div>
  );
}
