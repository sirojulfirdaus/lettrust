// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD FR-02.02–FR-02.08, FR-02.11; SA §11.3
"use client";

import { useState, type ChangeEvent, type FormEvent } from "react";
import { Upload } from "lucide-react";
import type { VerificationResponse } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ConsentCheckbox } from "@/components/verification/consent-checkbox";
import { GuidanceList } from "@/components/verification/guidance-list";
import { ModeSelector, type VerificationMode } from "@/components/verification/mode-selector";
import { ProcessingStatus } from "@/components/verification/processing-status";
import { ResultPanels } from "@/components/verification/result-panels";
import {
  afterSubmit,
  buildVerifyRequest,
  canToggleRisk,
  DEFAULT_MAX_UPLOAD_BYTES,
  initialFormState,
  shouldIncludeRisk,
  validatePdfFile,
  validateSubmission,
  withFile,
  withIncludeRisk,
  type VerifyFormState,
} from "@/lib/verification/form";
import { isValidReferenceCode, normalizeReferenceCode, REFERENCE_CODE_EXAMPLE } from "@/lib/verification/reference-code";

type ErrorFieldDetail = { field?: string };
type ApiErrorEnvelope = { error?: { code?: string; message?: string; details?: ErrorFieldDetail[] } };

// Memilih pesan perbaikan statis agar detail internal layanan tidak tampil kepada pemohon.
// Penolakan persetujuan AI dari BFF dikenali lewat details[].field "aiConsent".
export function verificationErrorMessage(status: number, code?: string, details?: ErrorFieldDetail[]): string {
  if (code === "VALIDATION_ERROR" && details?.some((detail) => detail.field === "aiConsent")) {
    return "Setujui pemrosesan AI sebelum mengirim surat untuk dianalisis.";
  }
  if (code === "INVALID_REFERENCE_CODE_FORMAT") return "Format kode referensi tidak valid. Periksa kembali kode pada surat Anda.";
  if (code === "INVALID_INPUT_COMBINATION") return "Masukkan kode referensi atau unggah berkas PDF untuk dianalisis.";
  if (code === "AI_ONLY_REQUIRES_INCLUDE_RISK") return "Tanpa kode referensi, pemeriksaan hanya dapat dilakukan dengan analisis AI. Setujui pemrosesan AI untuk melanjutkan.";
  if (code === "FILE_TOO_LARGE" || status === 413) return "Ukuran berkas melebihi batas yang diizinkan.";
  if (code === "UNSUPPORTED_MEDIA_TYPE" || status === 415) return "Berkas harus berformat PDF.";
  if (code === "EMPTY_FILE") return "Berkas kosong tidak dapat diproses.";
  if (code === "MULTIPLE_FILES") return "Hanya satu berkas yang dapat diproses per permintaan.";
  if (code === "RATE_LIMITED" || status === 429) return "Terlalu banyak permintaan. Coba lagi beberapa saat lagi.";
  if (status === 400 || code === "VALIDATION_ERROR") return "Periksa kembali kode referensi, pilihan mode, dan berkas yang Anda masukkan.";
  return "Layanan pemeriksaan sedang tidak tersedia. Coba lagi beberapa saat lagi.";
}

// Menjalankan validasi, meminta persetujuan per pengiriman, lalu mengirim multipart ke BFF portal.
// maxUploadBytes datang dari konfigurasi server lewat halaman; default hanya dipakai bila prop tidak diberikan.
export function VerifyForm({ maxUploadBytes = DEFAULT_MAX_UPLOAD_BYTES }: { maxUploadBytes?: number }) {
  // Dibulatkan ke bawah agar label tidak menjanjikan batas di atas nilai sebenarnya.
  const maxUploadMb = Math.floor((maxUploadBytes / (1024 * 1024)) * 10) / 10;
  const [form, setForm] = useState<VerifyFormState>(() => initialFormState());
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VerificationResponse | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [codeSubmitted, setCodeSubmitted] = useState(false);
  const { mode, referenceCode, file, includeRisk, consent } = form;
  const normalizedCode = normalizeReferenceCode(referenceCode);
  const riskRequested = shouldIncludeRisk(form);
  // Kesalahan format kode hanya tampil di bawah field (bukan juga di banner): saat diketik atau setelah dikirim.
  const codeInvalid = mode === "REFERENCE_CHECK" && !(normalizedCode && isValidReferenceCode(normalizedCode));
  const showCodeError = codeInvalid && (codeSubmitted || Boolean(normalizedCode));

  // Memvalidasi satu PDF di browser terhadap batas unggah server sebelum memulai permintaan.
  function acceptFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.currentTarget.files?.[0] ?? null;
    event.currentTarget.value = "";
    const rejection = selected ? validatePdfFile(selected, maxUploadBytes) : null;
    setFileError(rejection);
    setForm((current) => withFile(current, selected && !rejection ? selected : null));
  }

  // Menjaga input tetap relevan saat pemohon berpindah mode pemeriksaan.
  function changeMode(nextMode: VerificationMode) {
    setForm(initialFormState(nextMode));
    setFileError(null);
    setCodeSubmitted(false);
    setError(null);
    setResult(null);
  }

  // Mengirim kode dan berkas hanya ke route server portal, lalu menampilkan respons yang divalidasi.
  async function submitVerification(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationError = validateSubmission(form);
    // validateSubmission memeriksa format kode lebih dulu, jadi pesan ini sudah ditampilkan inline oleh showCodeError.
    setCodeSubmitted(codeInvalid);
    setError(codeInvalid ? null : validationError);
    // Fokus ke field kode agar pesan inline (aria-describedby) terbaca pembaca layar.
    if (codeInvalid) document.getElementById("reference-code")?.focus();
    if (validationError) return;

    setIsProcessing(true);
    setResult(null);
    try {
      const response = await fetch("/api/verify", { method: "POST", body: buildVerifyRequest(form) });
      const payload = await response.json() as VerificationResponse | ApiErrorEnvelope;
      if (!response.ok) {
        const apiError = (payload as ApiErrorEnvelope).error;
        setError(verificationErrorMessage(response.status, apiError?.code, apiError?.details));
        return;
      }
      if (!("proofCheck" in payload && "integrityCheck" in payload && "riskAnalysis" in payload)) {
        setError(verificationErrorMessage(502));
        return;
      }
      setResult(payload);
    } catch {
      setError(verificationErrorMessage(502));
    } finally {
      setIsProcessing(false);
      setForm(afterSubmit);
    }
  }

  // Menghapus semua masukan dan hasil ketika pemohon memulai pemeriksaan baru.
  function startAnotherCheck() {
    setForm(initialFormState());
    setError(null);
    setFileError(null);
    setCodeSubmitted(false);
    setResult(null);
  }

  return (
    <div className="space-y-6">
      <form onSubmit={submitVerification} className="space-y-6 rounded-lg border bg-card p-4 sm:p-6">
        <ModeSelector mode={mode} disabled={isProcessing} onChange={changeMode} />
        {mode === "REFERENCE_CHECK" && (
          <div className="space-y-2">
            <label htmlFor="reference-code" className="font-medium">Kode referensi</label>
            <Input id="reference-code" autoComplete="off" placeholder={REFERENCE_CODE_EXAMPLE} value={referenceCode} onChange={(event) => { const value = event.target.value; setForm((current) => ({ ...current, referenceCode: value })); }} disabled={isProcessing} aria-describedby={showCodeError ? "reference-help reference-error" : "reference-help"} aria-invalid={showCodeError} />
            <p id="reference-help" className="text-sm text-muted-foreground">Contoh: {REFERENCE_CODE_EXAMPLE}. Spasi dan tanda hubung akan dinormalisasi.</p>
            {showCodeError && <p id="reference-error" className="text-sm text-destructive">{verificationErrorMessage(400, "INVALID_REFERENCE_CODE_FORMAT")}</p>}
          </div>
        )}
        <div className="space-y-2">
          <label htmlFor="offer-letter" className="font-medium">Berkas surat {mode === "AI_ONLY" ? "(wajib PDF)" : `(opsional, PDF maksimal ${maxUploadMb} MB)`}</label>
          {/* Input berkas asli tetap ada (sr-only) agar data ke BFF tidak berubah; label di bawah berperan sebagai tombol. */}
          <div className="flex flex-wrap items-center gap-3">
            <input id="offer-letter" type="file" accept="application/pdf,.pdf" onChange={acceptFile} disabled={isProcessing} aria-describedby="file-help file-name" aria-invalid={Boolean(fileError)} className="peer sr-only" />
            <label htmlFor="offer-letter" className="inline-flex h-9 cursor-pointer items-center gap-2 rounded-md border border-border bg-card px-3 text-sm font-medium shadow-xs transition-colors hover:bg-muted peer-focus-visible:border-ring peer-focus-visible:ring-3 peer-focus-visible:ring-ring/50 peer-disabled:pointer-events-none peer-disabled:opacity-50">
              <Upload aria-hidden="true" size={16} strokeWidth={2} className="size-4" />
              Pilih berkas PDF
            </label>
            <span id="file-name" className="min-w-0 break-all text-sm text-muted-foreground">{file ? `${file.name} · ${(file.size / (1024 * 1024)).toFixed(2)} MB` : "Belum ada berkas dipilih"}</span>
            {file && <Button type="button" variant="outline" size="sm" disabled={isProcessing} onClick={() => setForm((current) => withFile(current, null))}>Hapus berkas</Button>}
          </div>
          <p id="file-help" className="text-sm text-muted-foreground">Berkas dipakai untuk pemeriksaan ini saja.</p>
          {fileError && <p role="alert" className="text-sm text-destructive">{fileError}</p>}
        </div>
        {mode === "REFERENCE_CHECK" && (
          <label className="flex items-start gap-3 rounded-lg border p-3">
            <input type="checkbox" className="mt-1 size-4 shrink-0 accent-primary" checked={includeRisk} disabled={!canToggleRisk(form) || isProcessing} onChange={(event) => { const checked = event.target.checked; setForm((current) => withIncludeRisk(current, checked)); }} />
            <span><span className="block font-medium">Analisis indikasi risiko dengan AI</span><span className="text-sm text-muted-foreground">Unggah PDF untuk mengaktifkan pilihan ini.</span></span>
          </label>
        )}
        {mode === "AI_ONLY" && <p className="rounded-lg bg-muted p-3 text-sm">Apabila perusahaan menyatakan menggunakan Lettrust, mintalah kode referensi kepada perusahaan.</p>}
        {riskRequested && <ConsentCheckbox checked={consent} disabled={isProcessing} onCheckedChange={(checked) => setForm((current) => ({ ...current, consent: checked }))} />}
        {error && <div role="alert" className="rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">{error}</div>}
        {isProcessing && <ProcessingStatus includeRisk={riskRequested} />}
        <Button type="submit" size="lg" disabled={isProcessing}>{isProcessing ? "Sedang memeriksa…" : "Periksa Surat"}</Button>
      </form>
      {result && (
        <div className="space-y-5">
          <ResultPanels result={result} />
          <GuidanceList result={result} />
          <Button type="button" variant="outline" onClick={startAnotherCheck}>Periksa surat lain</Button>
        </div>
      )}
    </div>
  );
}
