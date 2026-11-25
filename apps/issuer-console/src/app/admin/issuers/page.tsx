// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.05, §9.5; SA §10.5 (S-04)
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle, Building2, ChevronLeft, ChevronRight, Loader2, ShieldAlert } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import {
  formatIssuerTimestamp,
  IssuerStatusBadge,
} from "@/components/issuers/issuer-status-badge";
import {
  loadIssuerList,
  type IssuerListFilter,
  type IssuerListResponse,
} from "./admin-issuers-flow";

const PAGE_SIZE = 10;

const FILTER_OPTIONS: { value: IssuerListFilter; label: string }[] = [
  { value: "ALL", label: "Semua" },
  { value: "PENDING", label: "Menunggu Verifikasi" },
  { value: "VERIFIED", label: "Terverifikasi" },
  { value: "REJECTED", label: "Ditolak" },
];

type ListState =
  | { status: "loading" }
  | { status: "forbidden"; message: string }
  | { status: "error"; message: string }
  | { status: "ready"; data: IssuerListResponse };

// Halaman Daftar Penerbit untuk Administrator (S-04) dengan filter status dan paginasi.
export default function IssuerListPage() {
  const router = useRouter();
  const [filter, setFilter] = useState<IssuerListFilter>("ALL");
  const [offset, setOffset] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<ListState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    void loadIssuerList({
      status: filter,
      limit: PAGE_SIZE,
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
  }, [attempt, filter, offset, router]);

  // Mengubah filter status penerbit; abaikan jika filter aktif pada halaman pertama tidak berubah.
  const handleSelectFilter = (nextFilter: IssuerListFilter) => {
    if (nextFilter === filter && offset === 0) {
      return;
    }
    setState({ status: "loading" });
    setFilter(nextFilter);
    setOffset(0);
  };

  const handleRetry = () => {
    setState({ status: "loading" });
    setAttempt((n) => n + 1);
  };

  const handlePrevPage = () => {
    setState({ status: "loading" });
    setOffset((prev) => Math.max(0, prev - PAGE_SIZE));
  };

  const handleNextPage = () => {
    setState({ status: "loading" });
    setOffset((prev) => prev + PAGE_SIZE);
  };

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

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Daftar Penerbit</h1>
        <p className="text-sm text-muted-foreground">
          Tinjau pengajuan pendaftaran perusahaan penerbit dan kelola otorisasi akun HR.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Filter status penerbit">
        {FILTER_OPTIONS.map((option) => {
          const isActive = filter === option.value;
          return (
            <Button
              key={option.value}
              type="button"
              size="sm"
              variant={isActive ? "default" : "outline"}
              aria-pressed={isActive}
              onClick={() => handleSelectFilter(option.value)}
              className="cursor-pointer"
            >
              {option.label}
            </Button>
          );
        })}
      </div>

      <Card>
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Building2 className="size-5 text-primary" aria-hidden="true" />
            <span>Perusahaan Penerbit</span>
          </CardTitle>
          <CardDescription>
            {state.status === "ready"
              ? `Menampilkan ${state.data.items.length} dari ${state.data.total} penerbit.`
              : "Memuat daftar penerbit dari layanan backend."}
          </CardDescription>
        </CardHeader>

        <CardContent className="pt-6">
          {state.status === "loading" ? (
            <div
              role="status"
              aria-live="polite"
              className="flex items-center justify-center gap-2.5 py-12 text-sm text-muted-foreground"
            >
              <Loader2 className="size-5 animate-spin text-primary" aria-hidden="true" />
              <span>Memuat daftar penerbit...</span>
            </div>
          ) : state.status === "error" ? (
            <div className="space-y-4 py-4">
              <Alert variant="destructive">
                <AlertCircle className="size-4" aria-hidden="true" />
                <AlertTitle>Gagal memuat daftar penerbit</AlertTitle>
                <AlertDescription>{state.message}</AlertDescription>
              </Alert>
              <Button type="button" onClick={handleRetry} className="cursor-pointer">
                Coba lagi
              </Button>
            </div>
          ) : state.data.items.length === 0 ? (
            <div className="py-10 text-center">
              <p className="text-sm text-muted-foreground">
                {filter === "PENDING"
                  ? "Tidak ada penerbit yang menunggu verifikasi."
                  : "Belum ada penerbit untuk filter status ini."}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nama Perusahaan</TableHead>
                    <TableHead>Nomor Registrasi</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Tanggal Pengajuan</TableHead>
                    <TableHead className="text-right">Anggota HR</TableHead>
                    <TableHead className="text-right">Detail</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {state.data.items.map((item) => (
                    <TableRow key={item.issuerId}>
                      <TableCell className="font-medium">
                        <Link
                          href={`/admin/issuers/${encodeURIComponent(item.issuerId)}`}
                          className="text-primary underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                        >
                          {item.companyName}
                        </Link>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{item.registrationNumber}</TableCell>
                      <TableCell>
                        <IssuerStatusBadge status={item.issuerStatus} />
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {formatIssuerTimestamp(item.createdAt)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs">
                        {item.memberCount}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button asChild variant="outline" size="sm" className="cursor-pointer">
                          <Link href={`/admin/issuers/${encodeURIComponent(item.issuerId)}`}>
                            Tinjau
                          </Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {state.data.total > PAGE_SIZE ? (
                <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
                  <p className="text-xs text-muted-foreground">
                    Halaman {Math.floor(offset / PAGE_SIZE) + 1} dari{" "}
                    {Math.max(1, Math.ceil(state.data.total / PAGE_SIZE))}
                  </p>
                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={offset === 0}
                      onClick={handlePrevPage}
                      className="cursor-pointer"
                    >
                      <ChevronLeft className="size-4" aria-hidden="true" />
                      Sebelumnya
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={offset + PAGE_SIZE >= state.data.total}
                      onClick={handleNextPage}
                      className="cursor-pointer"
                    >
                      Berikutnya
                      <ChevronRight className="size-4" aria-hidden="true" />
                    </Button>
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
