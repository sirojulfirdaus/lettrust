// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-03.01–FR-03.06, §9.8; SA §10.6 (API-04), §11.2.3
"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AlertCircle, FileCheck2, FileUp, Loader2, RefreshCw, ShieldAlert } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { IssueProofResponse } from "@/lib/api/client";
import {
  formatFileSize,
  submitIssueProof,
  validateProofPdfFile,
} from "@/app/hr/proofs/proofs-flow";
import {
  EMPTY_ATTEMPT,
  applySubmitOutcome,
  canStartNewAttempt,
  isAttemptInputLocked,
  mayHaveBeenRecorded,
  resolveSubmitKey,
  startAttempt,
  type IdempotencyAttempt,
} from "@/app/hr/proofs/idempotency-attempt";

type ProofUploadFormProps = {
  onIssued: (proof: IssueProofResponse) => void;
  onUnauthorized: () => void;
};

type SubmitErrorState = {
  status: number;
  code: string;
  message: string;
  canRetrySameKey: boolean;
  requiresResetKey: boolean;
};

// Formulir unggah PDF final untuk penerbitan bukti (API-04) dengan konfirmasi dan Idempotency-Key per berkas.
export function ProofUploadForm({ onIssued, onUnauthorized }: ProofUploadFormProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [attempt, setAttempt] = useState<IdempotencyAttempt>(EMPTY_ATTEMPT);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<SubmitErrorState | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const isSubmittingRef = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  // Memvalidasi berkas yang dipilih dan membuat Idempotency-Key baru saat tidak ada upaya tertunda.
  const handleFilesSelected = (files: FileList | File[] | null) => {
    if (isSubmittingRef.current || attempt.locked) {
      return;
    }
    setSubmitError(null);
    const validation = validateProofPdfFile(files);
    if (!validation.valid) {
      setSelectedFile(null);
      setAttempt(EMPTY_ATTEMPT);
      setValidationError(validation.message);
      return;
    }
    setValidationError(null);
    setSelectedFile(validation.file);
    setAttempt(startAttempt());
  };

  // Mengosongkan berkas terpilih agar pengguna dapat memilih berkas PDF lain saat tidak terkunci.
  const handleClearFile = () => {
    if (isSubmittingRef.current || attempt.locked) {
      return;
    }
    setSelectedFile(null);
    setAttempt(EMPTY_ATTEMPT);
    setValidationError(null);
    setSubmitError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Membuang upaya tertunda secara eksplisit, mereset Idempotency-Key, dan membuka kembali pemilih berkas.
  const handleStartNewAttempt = () => {
    if (isSubmittingRef.current || (submitError !== null && !canStartNewAttempt(submitError))) {
      return;
    }
    setSelectedFile(null);
    setAttempt(EMPTY_ATTEMPT);
    setValidationError(null);
    setSubmitError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Membuat Idempotency-Key baru setelah terjadi konflik idempotensi (409 IDEMPOTENCY_KEY_CONFLICT).
  const handleResetIdempotencyKey = () => {
    if (isSubmittingRef.current || !selectedFile) {
      return;
    }
    setAttempt(startAttempt());
    setSubmitError(null);
  };

  // Mengirim berkas PDF ke API-04 menggunakan Idempotency-Key aktif dengan penjaga double-submit.
  const executeSubmit = async () => {
    if (isSubmittingRef.current || !selectedFile) {
      return;
    }
    const activeKey = resolveSubmitKey(attempt);

    isSubmittingRef.current = true;
    setIsSubmitting(true);
    setSubmitError(null);

    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const result = await submitIssueProof({
      file: selectedFile,
      idempotencyKey: activeKey,
      signal: controller.signal,
      onUnauthorized,
    });

    isSubmittingRef.current = false;
    setIsSubmitting(false);

    if (result.kind === "aborted") {
      return;
    }

    if (result.kind === "unauthorized") {
      setConfirmOpen(false);
      return;
    }

    setConfirmOpen(false);

    if (result.kind === "success") {
      setAttempt(applySubmitOutcome(activeKey, null));
      onIssued(result.data);
      return;
    }

    setAttempt(applySubmitOutcome(activeKey, result));
    setSubmitError({
      status: result.status,
      code: result.code,
      message: result.message,
      canRetrySameKey: result.canRetrySameKey,
      requiresResetKey: result.requiresResetKey,
    });
  };

  const isFilePickerDisabled = isAttemptInputLocked(attempt, isSubmitting);
  const allowNewAttempt = submitError === null || canStartNewAttempt(submitError);

  return (
    <Card>
      <CardHeader className="border-b">
        <CardTitle>Unggah Offer Letter Final (PDF)</CardTitle>
        <CardDescription>
          Pilih satu berkas PDF final berukuran maksimal 5 MB. Hash SHA-256 berkas akan dicatat ke
          registry blockchain tanpa menyimpan isi dokumen.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-5">
        <div
          onDragOver={(event) => {
            event.preventDefault();
            if (!isFilePickerDisabled) {
              setIsDragging(true);
            }
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setIsDragging(false);
            if (!isFilePickerDisabled) {
              handleFilesSelected(event.dataTransfer.files);
            }
          }}
          className={`rounded-lg border-2 border-dashed p-6 text-center transition-colors ${
            isDragging
              ? "border-primary bg-primary/5"
              : isFilePickerDisabled
                ? "border-border bg-muted/40 opacity-90"
                : "border-border bg-muted/30 hover:border-primary/50"
          }`}
        >
          <input
            ref={fileInputRef}
            id="proof-pdf-input"
            type="file"
            accept=".pdf,application/pdf"
            disabled={isFilePickerDisabled}
            onChange={(event) => handleFilesSelected(event.target.files)}
            className="sr-only"
          />

          <div className="mx-auto flex max-w-md flex-col items-center gap-3">
            <div className="flex size-11 items-center justify-center rounded-lg bg-primary/10 text-primary">
              {selectedFile ? (
                <FileCheck2 className="size-5" aria-hidden="true" />
              ) : (
                <FileUp className="size-5" aria-hidden="true" />
              )}
            </div>

            {selectedFile ? (
              <div className="space-y-1">
                <p className="text-sm font-semibold break-all text-foreground">
                  {selectedFile.name}
                </p>
                <p className="text-xs text-muted-foreground">
                  Ukuran: {formatFileSize(selectedFile.size)}{" "}
                  {attempt.locked
                    ? "(dikunci sementara untuk menjaga kunci idempotensi percobaan ulang)"
                    : "(PDF siap diverifikasi sebelum penerbitan)"}
                </p>
              </div>
            ) : (
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">
                  Tarik berkas PDF ke area ini atau pilih dari perangkat Anda
                </p>
                <p className="text-xs text-muted-foreground">
                  Hanya satu berkas PDF final, tidak kosong, ukuran maksimum 5 MB.
                </p>
              </div>
            )}

            <div className="flex flex-wrap items-center justify-center gap-2.5 pt-1">
              <Button
                type="button"
                variant={selectedFile ? "outline" : "default"}
                disabled={isFilePickerDisabled}
                onClick={() => fileInputRef.current?.click()}
                className={isFilePickerDisabled ? "cursor-not-allowed" : "cursor-pointer"}
              >
                {selectedFile ? "Ganti Berkas PDF" : "Pilih Berkas PDF"}
              </Button>
              {selectedFile ? (
                <Button
                  type="button"
                  variant="ghost"
                  disabled={isFilePickerDisabled}
                  onClick={handleClearFile}
                  className={isFilePickerDisabled ? "cursor-not-allowed" : "cursor-pointer"}
                >
                  Hapus Pilihan
                </Button>
              ) : null}
            </div>

            {attempt.locked ? (
              <p className="text-xs text-muted-foreground">
                Kunci idempotensi upaya sebelumnya dipertahankan agar percobaan ulang tetap aman.{" "}
                {allowNewAttempt ? (
                  <>
                    Gunakan &ldquo;Coba lagi&rdquo; atau klik &ldquo;Mulai ulang upaya baru&rdquo;
                    untuk mengganti berkas.
                  </>
                ) : (
                  <>Gunakan &ldquo;Coba lagi&rdquo; untuk mengulang permintaan yang sama.</>
                )}
              </p>
            ) : null}
          </div>
        </div>

        <label htmlFor="proof-pdf-input" className="sr-only">
          Berkas PDF Offer Letter Final
        </label>

        {validationError ? (
          <Alert variant="destructive">
            <AlertCircle className="size-4" aria-hidden="true" />
            <AlertTitle>Berkas tidak valid</AlertTitle>
            <AlertDescription>{validationError}</AlertDescription>
          </Alert>
        ) : null}

        {submitError ? (
          <Alert variant="destructive">
            <AlertCircle className="size-4" aria-hidden="true" />
            <AlertTitle>Penerbitan bukti gagal</AlertTitle>
            <AlertDescription className="space-y-3">
              <p>{submitError.message}</p>
              {mayHaveBeenRecorded(submitError) ? (
                <p>
                  Bila ragu apakah sudah tersimpan, periksa Daftar Bukti atau coba lagi dengan
                  permintaan yang sama.
                </p>
              ) : null}
              <div className="flex flex-wrap gap-2">
                {submitError.canRetrySameKey ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={isSubmitting || !selectedFile}
                    onClick={() => void executeSubmit()}
                    className={isSubmitting ? "cursor-not-allowed" : "cursor-pointer"}
                  >
                    <RefreshCw className="size-3.5" aria-hidden="true" />
                    Coba lagi
                  </Button>
                ) : null}
                {mayHaveBeenRecorded(submitError) ? (
                  <Button asChild size="sm" variant="ghost">
                    <Link href="/hr/proofs">Periksa Daftar Bukti</Link>
                  </Button>
                ) : null}
                {canStartNewAttempt(submitError) ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    disabled={isSubmitting}
                    onClick={handleStartNewAttempt}
                    className={isSubmitting ? "cursor-not-allowed" : "cursor-pointer"}
                  >
                    Mulai ulang upaya baru
                  </Button>
                ) : null}
                {submitError.requiresResetKey ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={isSubmitting || !selectedFile}
                    onClick={handleResetIdempotencyKey}
                    className={isSubmitting ? "cursor-not-allowed" : "cursor-pointer"}
                  >
                    Mulai ulang
                  </Button>
                ) : null}
              </div>
            </AlertDescription>
          </Alert>
        ) : null}

        <div className="rounded-lg border bg-muted/40 px-4 py-3 text-xs text-muted-foreground">
          Pastikan berkas yang diunggah sudah final dan tidak akan diedit atau disimpan ulang
          setelah penerbitan. Perubahan sekecil apa pun akan mengubah hash dokumen.
        </div>

        <div className="flex flex-wrap items-center justify-end gap-3 border-t pt-4">
          <Button
            type="button"
            size="lg"
            disabled={!selectedFile || isSubmitting}
            onClick={() => setConfirmOpen(true)}
            className={!selectedFile || isSubmitting ? "cursor-not-allowed" : "cursor-pointer"}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                Mencatat bukti ke registry...
              </>
            ) : (
              "Terbitkan Bukti"
            )}
          </Button>
        </div>
      </CardContent>

      <Dialog
        open={confirmOpen}
        onOpenChange={(nextOpen) => {
          if (!isSubmitting) {
            setConfirmOpen(nextOpen);
          }
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-md" showCloseButton={!isSubmitting}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ShieldAlert className="size-5 text-primary" aria-hidden="true" />
              Konfirmasi Penerbitan Bukti
            </DialogTitle>
            <DialogDescription>
              Periksa kembali berkas sebelum dicatat ke registry blockchain.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 text-sm text-foreground">
            {selectedFile ? (
              <div className="rounded-lg border bg-muted/50 px-3.5 py-2.5">
                <p className="font-medium break-all">{selectedFile.name}</p>
                <p className="text-xs text-muted-foreground">
                  Ukuran: {formatFileSize(selectedFile.size)}
                </p>
              </div>
            ) : null}
            <p className="text-muted-foreground">
              Berkas ini adalah versi final offer letter. Perubahan apa pun pada berkas setelah
              bukti diterbitkan akan menghasilkan hash berbeda dan terdeteksi sebagai berkas berbeda
              saat diverifikasi pelamar.
            </p>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={isSubmitting}
              onClick={() => setConfirmOpen(false)}
              className={isSubmitting ? "cursor-not-allowed" : "cursor-pointer"}
            >
              Batal
            </Button>
            <Button
              type="button"
              disabled={isSubmitting}
              onClick={() => void executeSubmit()}
              className={isSubmitting ? "cursor-not-allowed" : "cursor-pointer"}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                  Memproses...
                </>
              ) : (
                "Ya, Terbitkan Bukti"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
