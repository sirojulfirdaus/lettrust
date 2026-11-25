// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-03.08, §9.5; SA §10.6 (S-06)
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle, ChevronLeft, ChevronRight, FilePlus2, FileText, Loader2, ShieldAlert } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ProofStatusBadge, formatProofTimestamp } from "@/components/proofs/proof-status-badge";
import type { ProofListResponse } from "@/lib/api/client";
import {
  PROOF_LIST_PAGE_SIZE,
  loadProofList,
  type ProofFilterStatus,
} from "./proofs-flow";

type ProofListPageState =
  | { status: "loading" }
  | { status: "ready"; data: ProofListResponse }
  | { status: "forbidden"; message: string }
  | { status: "error"; message: string };

const FILTER_OPTIONS: readonly { value: ProofFilterStatus; label: string }[] = [
  { value: "ALL", label: "Semua" },
  { value: "ACTIVE", label: "Aktif" },
  { value: "REVOKED", label: "Dicabut" },
];

// Halaman Daftar Bukti penerbitan milik perusahaan HR (S-06 GET /api/v1/proofs).
export default function ProofListPage() {
  const router = useRouter();
  const [filter, setFilter] = useState<ProofFilterStatus>("ALL");
  const [offset, setOffset] = useState(0);
  const [reloadCount, setReloadCount] = useState(0);
  const [state, setState] = useState<ProofListPageState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    void loadProofList({
      status: filter,
      limit: PROOF_LIST_PAGE_SIZE,
      offset,
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
      if (result.kind === "error") {
        setState({ status: "error", message: result.message });
        return;
      }
      setState({ status: "ready", data: result.data });
    });

    return () => {
      controller.abort();
    };
  }, [filter, offset, reloadCount, router]);

  // Mengubah filter status dengan penjaga agar klik ulang filter aktif di halaman pertama tidak memicu loading kosong.
  const handleFilterChange = (nextFilter: ProofFilterStatus) => {
    if (nextFilter === filter && offset === 0) {
      return;
    }
    setState({ status: "loading" });
    setFilter(nextFilter);
    setOffset(0);
  };

  // Memuat ulang daftar bukti pada halaman dan filter aktif.
  const handleRetry = () => {
    setState({ status: "loading" });
    setReloadCount((n) => n + 1);
  };

  const total = state.status === "ready" ? state.data.total : 0;
  const hasPrev = offset > 0;
  const hasNext = state.status === "ready" && offset + PROOF_LIST_PAGE_SIZE < total;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Daftar Bukti</h1>
          <p className="text-sm text-muted-foreground">
            Riwayat bukti penerbitan offer letter yang aktif dan dicabut untuk perusahaan Anda.
          </p>
        </div>

        <Button asChild size="lg" className="cursor-pointer">
          <Link href="/hr/proofs/new">
            <FilePlus2 className="size-4" aria-hidden="true" />
            Terbitkan Bukti
          </Link>
        </Button>
      </div>

      {state.status === "forbidden" ? (
        <div className="space-y-4">
          <Alert variant="destructive">
            <ShieldAlert className="size-4" aria-hidden="true" />
            <AlertTitle>Akses tidak diizinkan</AlertTitle>
            <AlertDescription>{state.message}</AlertDescription>
          </Alert>
          <Button asChild variant="outline" className="cursor-pointer">
            <Link href="/hr">Kembali ke Beranda HR</Link>
          </Button>
        </div>
      ) : (
        <Card>
          <CardHeader className="border-b">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <CardTitle>Riwayat Bukti Penerbitan</CardTitle>
                  {state.status === "ready" ? (
                    <Badge variant="secondary">Total: {state.data.total}</Badge>
                  ) : null}
                </div>
                <CardDescription>
                  Status pada tabel dibaca dari cermin off-chain. Buka halaman detail untuk
                  memeriksa status langsung dari registry blockchain.
                </CardDescription>
              </div>

              <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Filter status bukti">
                {FILTER_OPTIONS.map((option) => {
                  const isActive = filter === option.value;
                  return (
                    <Button
                      key={option.value}
                      type="button"
                      size="sm"
                      variant={isActive ? "default" : "outline"}
                      aria-pressed={isActive}
                      onClick={() => handleFilterChange(option.value)}
                      className="cursor-pointer"
                    >
                      {option.label}
                    </Button>
                  );
                })}
              </div>
            </div>
          </CardHeader>

          <CardContent className="space-y-4">
            {state.status === "loading" ? (
              <div
                role="status"
                aria-live="polite"
                className="flex flex-col items-center justify-center gap-2.5 py-12 text-center"
              >
                <Loader2 className="size-6 animate-spin text-primary" aria-hidden="true" />
                <p className="text-sm text-muted-foreground">Memuat daftar bukti penerbitan...</p>
              </div>
            ) : state.status === "error" ? (
              <div className="space-y-3 py-4">
                <Alert variant="destructive">
                  <AlertCircle className="size-4" aria-hidden="true" />
                  <AlertTitle>Gagal memuat daftar bukti</AlertTitle>
                  <AlertDescription>{state.message}</AlertDescription>
                </Alert>
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleRetry}
                  className="cursor-pointer"
                >
                  Coba lagi
                </Button>
              </div>
            ) : state.data.items.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
                <div className="flex size-11 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                  <FileText className="size-5" aria-hidden="true" />
                </div>
                {filter === "ALL" ? (
                  <>
                    <div className="space-y-1">
                      <p className="text-sm font-semibold text-foreground">
                        Belum ada bukti penerbitan
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Terbitkan bukti pertama Anda untuk membantu pihak penerima memverifikasi
                        bukti penerbitan surat penawaran kerja Anda.
                      </p>
                    </div>
                    <Button asChild className="cursor-pointer">
                      <Link href="/hr/proofs/new">
                        <FilePlus2 className="size-4" aria-hidden="true" />
                        Terbitkan Bukti Pertama
                      </Link>
                    </Button>
                  </>
                ) : (
                  <>
                    <div className="space-y-1">
                      <p className="text-sm font-semibold text-foreground">
                        Tidak ada bukti dengan status {filter === "ACTIVE" ? "Aktif" : "Dicabut"}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Ubah filter untuk melihat seluruh bukti penerbitan perusahaan Anda.
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => handleFilterChange("ALL")}
                      className="cursor-pointer"
                    >
                      Tampilkan Semua
                    </Button>
                  </>
                )}
              </div>
            ) : (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Kode Referensi</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Waktu Penerbitan</TableHead>
                      <TableHead>Waktu Pencabutan</TableHead>
                      <TableHead className="text-right">Tindakan</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {state.data.items.map((item) => (
                      <TableRow key={item.proofId}>
                        <TableCell>
                          <Link
                            href={`/hr/proofs/${encodeURIComponent(item.proofId)}`}
                            className="font-mono text-sm font-semibold text-primary underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                          >
                            {item.referenceCode}
                          </Link>
                        </TableCell>
                        <TableCell>
                          <ProofStatusBadge status={item.lifecycleStatus} />
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {formatProofTimestamp(item.issuedAt)}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {item.revokedAt ? formatProofTimestamp(item.revokedAt) : "-"}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button asChild variant="outline" size="sm" className="cursor-pointer">
                            <Link href={`/hr/proofs/${encodeURIComponent(item.proofId)}`}>
                              Lihat Detail
                            </Link>
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                {total > PROOF_LIST_PAGE_SIZE ? (
                  <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
                    <p className="text-xs text-muted-foreground">
                      Menampilkan {offset + 1} sampai{" "}
                      {Math.min(offset + state.data.items.length, total)} dari {total} bukti
                    </p>
                    <div className="flex items-center gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={!hasPrev}
                        onClick={() => {
                          setState({ status: "loading" });
                          setOffset((prev) => Math.max(0, prev - PROOF_LIST_PAGE_SIZE));
                        }}
                        className={hasPrev ? "cursor-pointer" : "cursor-not-allowed"}
                      >
                        <ChevronLeft className="size-4" aria-hidden="true" />
                        Sebelumnya
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={!hasNext}
                        onClick={() => {
                          setState({ status: "loading" });
                          setOffset((prev) => prev + PROOF_LIST_PAGE_SIZE);
                        }}
                        className={hasNext ? "cursor-pointer" : "cursor-not-allowed"}
                      >
                        Berikutnya
                        <ChevronRight className="size-4" aria-hidden="true" />
                      </Button>
                    </div>
                  </div>
                ) : null}
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
