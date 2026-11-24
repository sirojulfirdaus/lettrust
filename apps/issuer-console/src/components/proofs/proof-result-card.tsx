// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-03.07, §9.10; SA §10.6 (API-04)
"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Check, CheckCircle2, Copy, ExternalLink, FilePlus2 } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ProofStatusBadge, formatProofTimestamp } from "@/components/proofs/proof-status-badge";
import type { IssueProofResponse } from "@/lib/api/client";

type ProofResultCardProps = {
  proof: IssueProofResponse;
  onIssueAnother: () => void;
};

type CopyField = "referenceCode" | "proofId" | "documentHash" | "txHash";

// Menampilkan hasil penerbitan bukti (FR-03.07 & §9.10) lengkap dengan tombol salin dan instruksi pengiriman.
export function ProofResultCard({ proof, onIssueAnother }: ProofResultCardProps) {
  const [copiedField, setCopiedField] = useState<CopyField | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, []);

  // Menyalin nilai teks ke clipboard dengan umpan balik singkat untuk pengguna.
  const handleCopy = async (field: CopyField, value: string) => {
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(value);
      }
      setCopiedField(field);
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
      timerRef.current = setTimeout(() => {
        setCopiedField(null);
      }, 2000);
    } catch {
      setCopiedField(null);
    }
  };

  return (
    <div className="space-y-5">
      <Alert className="border-status-positive/30 bg-status-positive/10 text-foreground">
        <CheckCircle2 className="size-4 text-status-positive" aria-hidden="true" />
        <AlertTitle className="text-status-positive">Bukti penerbitan berhasil dicatat</AlertTitle>
        <AlertDescription className="text-foreground">
          Transaksi penerbitan telah terkonfirmasi di registry blockchain pada blok #
          {proof.transaction.blockNumber}.
        </AlertDescription>
      </Alert>

      <Card>
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <CardTitle>Kode Referensi Bukti</CardTitle>
              <CardDescription>
                Bagikan kode referensi ini bersama berkas PDF final kepada pelamar.
              </CardDescription>
            </div>
            <ProofStatusBadge status={proof.lifecycleStatus} />
          </div>
        </CardHeader>

        <CardContent className="space-y-5">
          <div className="flex flex-col gap-3 rounded-lg border bg-muted/40 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0 space-y-1">
              <p className="text-xs font-medium text-muted-foreground">Kode Referensi</p>
              <p className="font-mono text-xl font-bold tracking-wide break-all text-primary">
                {proof.referenceCode}
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              onClick={() => void handleCopy("referenceCode", proof.referenceCode)}
              className="shrink-0 cursor-pointer"
            >
              {copiedField === "referenceCode" ? (
                <>
                  <Check className="size-4 text-status-positive" aria-hidden="true" />
                  Tersalin
                </>
              ) : (
                <>
                  <Copy className="size-4" aria-hidden="true" />
                  Salin Kode
                </>
              )}
            </Button>
          </div>

          <div className="rounded-lg border border-primary/20 bg-primary/5 px-4 py-3 text-sm text-foreground">
            <p className="font-semibold">Instruksi pengiriman ke pelamar</p>
            <p className="mt-1 text-muted-foreground">
              Kirim berkas PDF yang sama persis beserta kode referensi di atas melalui kanal resmi
              perusahaan. Jangan ubah, kompres ulang, atau simpan ulang berkas karena perubahan
              sekecil apa pun akan membuat hash tidak cocok saat diverifikasi.
            </p>
          </div>

          <dl className="grid gap-4 border-t pt-4 sm:grid-cols-2">
            <div className="space-y-1">
              <dt className="text-xs font-medium text-muted-foreground">Waktu Penerbitan</dt>
              <dd className="text-sm font-medium text-foreground">
                {formatProofTimestamp(proof.issuedAt)}
              </dd>
            </div>

            <div className="space-y-1">
              <dt className="text-xs font-medium text-muted-foreground">Nomor Blok Registry</dt>
              <dd className="font-mono text-sm font-medium text-foreground">
                #{proof.transaction.blockNumber}
              </dd>
            </div>

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
              <dt className="text-xs font-medium text-muted-foreground">
                Hash Dokumen ({proof.hashAlgorithm})
              </dt>
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

            <div className="space-y-1 sm:col-span-2">
              <dt className="text-xs font-medium text-muted-foreground">Hash Transaksi Registry</dt>
              <dd className="flex items-start justify-between gap-2">
                <span className="font-mono text-xs break-all text-foreground">
                  {proof.transaction.hash}
                </span>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  aria-label="Salin Hash Transaksi"
                  onClick={() => void handleCopy("txHash", proof.transaction.hash)}
                  className="h-7 shrink-0 cursor-pointer px-2 text-xs"
                >
                  {copiedField === "txHash" ? (
                    <Check className="size-3.5 text-status-positive" aria-hidden="true" />
                  ) : (
                    <Copy className="size-3.5" aria-hidden="true" />
                  )}
                </Button>
              </dd>
            </div>
          </dl>

          <div className="flex flex-wrap items-center gap-3 border-t pt-4">
            <Button asChild className="cursor-pointer">
              <Link href={`/hr/proofs/${encodeURIComponent(proof.proofId)}`}>
                <ExternalLink className="size-4" aria-hidden="true" />
                Lihat Detail Bukti
              </Link>
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={onIssueAnother}
              className="cursor-pointer"
            >
              <FilePlus2 className="size-4" aria-hidden="true" />
              Terbitkan Bukti Lain
            </Button>
            <Button asChild variant="ghost" className="cursor-pointer">
              <Link href="/hr/proofs">Ke Daftar Bukti</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
