// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD FR-02.02–FR-02.08, FR-02.11; SA §11.3
"use client";

import { useState, type ChangeEvent, type FormEvent } from "react";
import type { VerificationResponse } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ConsentCheckbox } from "@/components/verification/consent-checkbox";
import { GuidanceList } from "@/components/verification/guidance-list";
import { ModeSelector, type VerificationMode } from "@/components/verification/mode-selector";
import { ProcessingStatus } from "@/components/verification/processing-status";
import { ResultPanels } from "@/components/verification/result-panels";
import { isValidReferenceCode, normalizeReferenceCode, REFERENCE_CODE_EXAMPLE } from "@/lib/verification/reference-code";

const MAX_FILE_BYTES = 5 * 1024 * 1024;
const PDF_MIME = "application/pdf";

type ApiErrorEnvelope = { error?: { code?: string; message?: string } };

// Memilih pesan perbaikan statis agar detail internal layanan tidak tampil kepada pemohon.
export function verificationErrorMessage(status: number, code?: string): string {
  if (status === 400 || code === "VALIDATION_ERROR" || code === "INVALID_REFERENCE_CODE_FORMAT" || code === "INVALID_INPUT_COMBINATION" || code === "AI_ONLY_REQUIRES_INCLUDE_RISK") {
    return "Periksa kembali kode referensi, pilihan mode, dan berkas yang Anda masukkan.";
  }
  if (status === 413 || code === "FILE_TOO_LARGE") return "Ukuran PDF melebihi batas 5 MB. Pilih berkas yang lebih kecil.";
  if (status === 415 || code === "UNSUPPORTED_MEDIA_TYPE") return "Format berkas tidak didukung. Pilih dokumen PDF.";
  if (code === "EMPTY_FILE") return "Berkas kosong. Pilih PDF lain yang berisi surat.";
  if (code === "MULTIPLE_FILES") return "Pilih satu berkas PDF untuk diperiksa.";
  return "Layanan pemeriksaan sedang tidak tersedia. Coba lagi beberapa saat lagi.";
}

// Menjalankan validasi, meminta persetujuan per pengiriman, lalu mengirim multipart ke BFF portal.
export function VerifyForm() {
  const [mode, setMode] = useState<VerificationMode>("REFERENCE_CHECK");
  const [referenceCode, setReferenceCode] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [includeRisk, setIncludeRisk] = useState(false);
  const [consent, setConsent] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VerificationResponse | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const normalizedCode = normalizeReferenceCode(referenceCode);
  const shouldIncludeRisk = mode === "AI_ONLY" || includeRisk;

  // Memvalidasi satu PDF di browser sebelum memulai permintaan.
  function acceptFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.currentTarget.files?.[0] ?? null;
    event.currentTarget.value = "";
    setFileError(null);
    setFile(null);
    setConsent(false);
    if (!selected) return;
    if (!selected.name.toLowerCase().endsWith(".pdf") || (selected.type && selected.type !== PDF_MIME)) {
      setFileError("Pilih berkas dengan format PDF.");
      return;
    }
    if (selected.size === 0) {
      setFileError("Berkas kosong. Pilih PDF lain yang berisi surat.");
      return;
    }
    if (selected.size > MAX_FILE_BYTES) {
      setFileError("Ukuran PDF melebihi batas 5 MB.");
      return;
    }
    setFile(selected);
  }

  // Menjaga input tetap relevan saat pemohon berpindah mode pemeriksaan.
  function changeMode(nextMode: VerificationMode) {
    setMode(nextMode);
    setReferenceCode("");
    setFile(null);
    setIncludeRisk(nextMode === "AI_ONLY");
    setConsent(false);
    setFileError(null);
    setError(null);
    setResult(null);
  }

  // Mengirim kode dan berkas hanya ke route server portal, lalu menampilkan respons yang divalidasi.
  async function submitVerification(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (mode === "REFERENCE_CHECK" && (!normalizedCode || !isValidReferenceCode(normalizedCode))) {
      setError("Masukkan kode referensi dengan format yang benar, misalnya LTR-7K3M-9QX2-H4TD.");
      return;
    }
    if ((mode === "AI_ONLY" || shouldIncludeRisk) && !file) {
      setError("Pilih PDF sebelum meminta analisis isi surat.");
      return;
    }
    if (shouldIncludeRisk && !consent) {
      setError("Setujui pemrosesan AI sebelum mengirim surat untuk dianalisis.");
      return;
    }

    setIsProcessing(true);
    setResult(null);
    const formData = new FormData();
    formData.set("includeRisk", String(shouldIncludeRisk));
    if (mode === "REFERENCE_CHECK" && normalizedCode) formData.set("referenceCode", normalizedCode);
    if (file) formData.set("file", file, file.name);
    try {
      const response = await fetch("/api/verify", { method: "POST", body: formData });
      const payload = await response.json() as VerificationResponse | ApiErrorEnvelope;
      if (!response.ok) {
        setError(verificationErrorMessage(response.status, (payload as ApiErrorEnvelope).error?.code));
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
      setConsent(false);
    }
  }

  // Menghapus semua masukan dan hasil ketika pemohon memulai pemeriksaan baru.
  function startAnotherCheck() {
    setReferenceCode("");
    setFile(null);
    setIncludeRisk(false);
    setConsent(false);
    setError(null);
    setFileError(null);
    setResult(null);
    setMode("REFERENCE_CHECK");
  }

  return (
    <div className="space-y-6">
      <form onSubmit={submitVerification} className="space-y-6 rounded-xl border bg-card p-4 sm:p-6">
        <ModeSelector mode={mode} disabled={isProcessing} onChange={changeMode} />
        {mode === "REFERENCE_CHECK" && (
          <div className="space-y-2">
            <label htmlFor="reference-code" className="font-medium">Kode referensi</label>
            <Input id="reference-code" autoComplete="off" placeholder={REFERENCE_CODE_EXAMPLE} value={referenceCode} onChange={(event) => setReferenceCode(event.target.value)} disabled={isProcessing} aria-describedby="reference-help" aria-invalid={Boolean(referenceCode && normalizedCode && !isValidReferenceCode(normalizedCode))} />
            <p id="reference-help" className="text-sm text-muted-foreground">Contoh: {REFERENCE_CODE_EXAMPLE}. Spasi dan tanda hubung akan dinormalisasi.</p>
            {referenceCode && normalizedCode && !isValidReferenceCode(normalizedCode) && <p className="text-sm text-destructive">Format kode belum sesuai.</p>}
          </div>
        )}
        <div className="space-y-2">
          <label htmlFor="offer-letter" className="font-medium">Berkas surat {mode === "AI_ONLY" ? "(wajib PDF)" : "(opsional, PDF maksimal 5 MB)"}</label>
          <Input id="offer-letter" type="file" accept="application/pdf,.pdf" onChange={acceptFile} disabled={isProcessing} aria-describedby="file-help" aria-invalid={Boolean(fileError)} />
          <p id="file-help" className="text-sm text-muted-foreground">Berkas dipakai untuk pemeriksaan ini saja.</p>
          {fileError && <p role="alert" className="text-sm text-destructive">{fileError}</p>}
          {file && <div className="flex flex-wrap items-center gap-3 text-sm"><span>{file.name} · {(file.size / (1024 * 1024)).toFixed(2)} MB</span><Button type="button" variant="outline" size="sm" disabled={isProcessing} onClick={() => { setFile(null); setConsent(false); }}>Hapus berkas</Button></div>}
        </div>
        {mode === "REFERENCE_CHECK" && (
          <label className="flex items-start gap-3 rounded-lg border p-3">
            <input type="checkbox" checked={includeRisk} disabled={!file || isProcessing} onChange={(event) => { setIncludeRisk(event.target.checked); setConsent(false); }} />
            <span><span className="block font-medium">Analisis indikasi risiko dengan AI</span><span className="text-sm text-muted-foreground">Unggah PDF untuk mengaktifkan pilihan ini.</span></span>
          </label>
        )}
        {mode === "AI_ONLY" && <p className="rounded-lg bg-muted p-3 text-sm">Bukti penerbitan dan keutuhan berkas tidak diperiksa tanpa kode referensi.</p>}
        {shouldIncludeRisk && <ConsentCheckbox checked={consent} disabled={isProcessing} onCheckedChange={setConsent} />}
        {error && <div role="alert" className="rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">{error}</div>}
        {isProcessing && <ProcessingStatus includeRisk={shouldIncludeRisk} />}
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
