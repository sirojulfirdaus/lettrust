// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-03.08, FR-03.09, FR-04.01–FR-04.07, §9.10; SA §10.6 (API-05, API-06), §11.2.3
"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  Check,
  CheckCircle2,
  Copy,
  FileSearch,
  Loader2,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ProofStatusBadge,
  formatProofTimestamp,
  getRevocationReasonLabel,
} from "@/components/proofs/proof-status-badge";
import { RevokeDialog } from "@/components/proofs/revoke-dialog";
import type { ProofStatusResponse, RevocationReasonCode, RevokeProofResponse } from "@/lib/api/client";
import { loadProofDetail } from "../proofs-flow";

type ProofDetailState =
  | { status: "loading" }
  | { status: "ready"; data: ProofStatusResponse }
  | { status: "not_found"; message: string }
  | { status: "forbidden"; message: string }
  | { status: "error"; message: string };

type CopyField = "referenceCode" | "proofId" | "documentHash" | "issueTx" | "revokeTx";

// Memparsing parameter proofId dari URL secara aman.
function decodeProofId(raw: string | string[] | undefined): string {
  const value = Array.isArray(raw) ? raw[0] ?? "" : raw ?? "";
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

// Halaman Detail Bukti (API-05) dan tindakan pencabutan bukti ACTIVE (API-06).
export default function ProofDetailPage() {
  const params = useParams<{ proofId?: string }>();
  const router = useRouter();
  const proofId = decodeProofId(params?.proofId);

  const [reloadCount, setReloadCount] = useState(0);
  const [state, setState] = useState<ProofDetailState>(() =>
    proofId
      ? { status: "loading" }
      : { status: "not_found", message: "Bukti tidak ditemukan." },
  );
  const [revokeConflictMessage, setRevokeConflictMessage] = useState<string | null>(null);
  const [revokeSuccessMessage, setRevokeSuccessMessage] = useState<string | null>(null);
  const [copiedField, setCopiedField] = useState<CopyField | null>(null);
  const copyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (copyTimerRef.current) {
        clearTimeout(copyTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!proofId) {
      return;
    }

    const controller = new AbortController();
    void loadProofDetail({
      proofId,
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
      if (result.kind === "not_found") {
        setState({ status: "not_found", message: result.message });
        return;
      }
      if (result.kind === "forbidden") {
        setState({ status: "forbidden", message: result.message });
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
  }, [proofId, reloadCount, router]);

  // Menyalin nilai teks ke clipboard dengan umpan balik singkat.
  const handleCopy = async (field: CopyField, value: string) => {
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(value);
      }
      setCopiedField(field);
      if (copyTimerRef.current) {
        clearTimeout(copyTimerRef.current);
      }
      copyTimerRef.current = setTimeout(() => {
        setCopiedField(null);
      }, 2000);
    } catch {
      setCopiedField(null);
    }
  };

  // Memperbarui tampilan saat pencabutan berhasil dan menyegarkan data dari registry (API-05).
  const handleRevoked = (result: RevokeProofResponse, reasonCode: RevocationReasonCode) => {
    setRevokeConflictMessage(null);
    setRevokeSuccessMessage(
      `Bukti berhasil dicabut dan terkonfirmasi pada blok #${result.transaction.blockNumber}.`,
    );
    setState((prev) => {
      if (prev.status !== "ready") {
        return prev;
      }
      return {
        status: "ready",
        data: {
          ...prev.data,
          lifecycleStatus: result.lifecycleStatus,
          revokedAt: result.revokedAt,
          revocationReasonCode: reasonCode,
          revokeTransaction: result.transaction,
        },
      };
    });
    setReloadCount((n) => n + 1);
  };

  // Menyimpan pesan konflik 409 PROOF_ALREADY_REVOKED di halaman detail agar tetap tampil setelah refresh.
  const handleAlreadyRevoked = (message: string) => {
    setRevokeSuccessMessage(null);
    setRevokeConflictMessage(message);
    setReloadCount((n) => n + 1);
  };

  if (state.status === "loading") {
    return (
      <div
        role="status"
        aria-live="polite"
        className="mx-auto flex max-w-md flex-col items-center justify-center gap-3 py-16 text-center"
      >
        <Loader2 className="size-6 animate-spin text-primary" aria-hidden="true" />
        <p className="text-sm text-muted-foreground">Memuat detail bukti dari registry...</p>
      </div>
    );
  }

  if (state.status === "not_found") {
    return (
      <div className="mx-auto max-w-lg space-y-4 py-8">
        <Alert>
          <FileSearch className="size-4" aria-hidden="true" />
          <AlertTitle>Bukti tidak ditemukan</AlertTitle>
          <AlertDescription>{state.message}</AlertDescription>
        </Alert>
        <Button asChild variant="outline" className="cursor-pointer">
          <Link href="/hr/proofs">
            <ArrowLeft className="size-4" aria-hidden="true" />
            Kembali ke Daftar Bukti
          </Link>
        </Button>
      </div>
    );
  }

  if (state.status === "forbidden") {
    return (
      <div className="mx-auto max-w-lg space-y-4 py-8">
        <Alert variant="destructive">
          <ShieldAlert className="size-4" aria-hidden="true" />
          <AlertTitle>Akses tidak diizinkan</AlertTitle>
          <AlertDescription>{state.message}</AlertDescription>
        </Alert>
        <Button asChild variant="outline" className="cursor-pointer">
          <Link href="/hr">Kembali ke Beranda HR</Link>
        </Button>
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="mx-auto max-w-lg space-y-4 py-8">
        <Alert variant="destructive">
          <AlertCircle className="size-4" aria-hidden="true" />
          <AlertTitle>Gagal memuat detail bukti</AlertTitle>
          <AlertDescription>{state.message}</AlertDescription>
        </Alert>
        <div className="flex flex-wrap gap-3">
          <Button
            type="button"
            onClick={() => {
              setState({ status: "loading" });
              setReloadCount((n) => n + 1);
            }}
            className="cursor-pointer"
          >
            Coba lagi
          </Button>
          <Button asChild variant="outline" className="cursor-pointer">
            <Link href="/hr/proofs">Kembali ke Daftar Bukti</Link>
          </Button>
        </div>
      </div>
    );
  }

  const proof = state.data;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Detail Bukti</h1>
          <p className="text-sm text-muted-foreground">
            Status dan hash dokumen dibaca langsung dari registry blockchain.
          </p>
        </div>

        <Button asChild variant="outline" size="sm" className="cursor-pointer">
          <Link href="/hr/proofs">
            <ArrowLeft className="size-4" aria-hidden="true" />
            Daftar Bukti
          </Link>
        </Button>
      </div>

      {revokeSuccessMessage ? (
        <Alert className="border-status-positive/30 bg-status-positive/10 text-foreground">
          <CheckCircle2 className="size-4 text-status-positive" aria-hidden="true" />
          <AlertTitle className="text-status-positive">Bukti dicabut</AlertTitle>
          <AlertDescription className="text-foreground">{revokeSuccessMessage}</AlertDescription>
        </Alert>
      ) : null}

      {revokeConflictMessage ? (
        <Alert className="border-status-warning/40 bg-status-warning/10 text-foreground">
          <AlertTriangle className="size-4 text-status-warning" aria-hidden="true" />
          <AlertTitle className="text-status-warning">Status bukti telah berubah</AlertTitle>
          <AlertDescription className="text-foreground">{revokeConflictMessage}</AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <CardTitle className="font-mono text-lg">{proof.referenceCode}</CardTitle>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  aria-label="Salin Kode Referensi"
                  onClick={() => void handleCopy("referenceCode", proof.referenceCode)}
                  className="h-7 cursor-pointer px-2 text-xs"
                >
                  {copiedField === "referenceCode" ? (
                    <>
                      <Check className="size-3.5 text-status-positive" aria-hidden="true" />
                      <span>Tersalin</span>
                    </>
                  ) : (
                    <>
                      <Copy className="size-3.5" aria-hidden="true" />
                      <span>Salin</span>
                    </>
                  )}
                </Button>
              </div>
              <CardDescription>ID Penerbit: {proof.issuerId}</CardDescription>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <ProofStatusBadge status={proof.lifecycleStatus} />
              <Badge variant="secondary" className="gap-1">
                <ShieldCheck className="size-3.5" aria-hidden="true" />
                <span>Sumber: {proof.source}</span>
              </Badge>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-5">
          <dl className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1 sm:col-span-2">
              <dt className="text-xs font-medium text-muted-foreground">ID Bukti (Proof ID)</dt>
              <dd className="flex items-start justify-between gap-2">
                <span className="font-mono text-xs break-all text-foreground">{proof.proofId}</span>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  aria-label="Salin ID Bukti"
                  onClick={() => void handleCopy("proofId", proof.proofId)}
                  className="h-7 shrink-0 cursor-pointer px-2 text-xs"
                >
                  {copiedField === "proofId" ? (
                    <Check className="size-3.5 text-status-positive" aria-hidden="true" />
                  ) : (
                    <Copy className="size-3.5" aria-hidden="true" />
                  )}
                </Button>
              </dd>
            </div>

            <div className="space-y-1 sm:col-span-2">
              <dt className="text-xs font-medium text-muted-foreground">Hash Dokumen (SHA-256)</dt>
              <dd className="flex items-start justify-between gap-2">
                <span className="font-mono text-xs break-all text-foreground">
                  {proof.documentHash}
                </span>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  aria-label="Salin Hash Dokumen"
                  onClick={() => void handleCopy("documentHash", proof.documentHash)}
                  className="h-7 shrink-0 cursor-pointer px-2 text-xs"
                >
                  {copiedField === "documentHash" ? (
                    <Check className="size-3.5 text-status-positive" aria-hidden="true" />
                  ) : (
                    <Copy className="size-3.5" aria-hidden="true" />
                  )}
                </Button>
              </dd>
            </div>
          </dl>

          <div className="space-y-3 border-t pt-4">
            <h2 className="text-sm font-semibold text-foreground">Riwayat Siklus Hidup</h2>

            <div className="rounded-lg border bg-muted/30 p-4 space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-sm font-medium text-foreground">Penerbitan Bukti</span>
                <span className="text-xs text-muted-foreground">
                  {formatProofTimestamp(proof.issuedAt)}
                </span>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                <span>Blok #{proof.issueTransaction.blockNumber}</span>
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className="font-mono break-all text-foreground">
                    {proof.issueTransaction.hash}
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    aria-label="Salin Hash Transaksi Penerbitan"
                    onClick={() => void handleCopy("issueTx", proof.issueTransaction.hash)}
                    className="h-6 shrink-0 cursor-pointer px-1.5"
                  >
                    {copiedField === "issueTx" ? (
                      <Check className="size-3 text-status-positive" aria-hidden="true" />
                    ) : (
                      <Copy className="size-3" aria-hidden="true" />
                    )}
                  </Button>
                </div>
              </div>
            </div>

            {proof.lifecycleStatus === "REVOKED" ? (
              <div className="rounded-lg border border-status-warning/40 bg-status-warning/5 p-4 space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-medium text-foreground">Pencabutan Bukti</span>
                  <span className="text-xs text-muted-foreground">
                    {proof.revokedAt ? formatProofTimestamp(proof.revokedAt) : "-"}
                  </span>
                </div>
                {proof.revocationReasonCode ? (
                  <p className="text-xs text-foreground">
                    Alasan:{" "}
                    <span className="font-medium">
                      {getRevocationReasonLabel(proof.revocationReasonCode)}
                    </span>{" "}
                    <span className="font-mono text-muted-foreground">
                      ({proof.revocationReasonCode})
                    </span>
                  </p>
                ) : null}
                {proof.revokeTransaction ? (
                  <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                    <span>Blok #{proof.revokeTransaction.blockNumber}</span>
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="font-mono break-all text-foreground">
                        {proof.revokeTransaction.hash}
                      </span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        aria-label="Salin Hash Transaksi Pencabutan"
                        onClick={() =>
                          void handleCopy("revokeTx", proof.revokeTransaction?.hash ?? "")
                        }
                        className="h-6 shrink-0 cursor-pointer px-1.5"
                      >
                        {copiedField === "revokeTx" ? (
                          <Check className="size-3 text-status-positive" aria-hidden="true" />
                        ) : (
                          <Copy className="size-3" aria-hidden="true" />
                        )}
                      </Button>
                    </div>
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        </CardContent>
      </Card>

      {proof.lifecycleStatus === "ACTIVE" ? (
        <RevokeDialog
          key={proof.proofId}
          proofId={proof.proofId}
          referenceCode={proof.referenceCode}
          onRevoked={handleRevoked}
          onAlreadyRevoked={handleAlreadyRevoked}
          onUnauthorized={() => router.replace("/login?reason=session_expired")}
        />
      ) : null}
    </div>
  );
}
