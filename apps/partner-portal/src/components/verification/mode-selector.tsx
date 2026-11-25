// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD FR-02.02, §9.4
"use client";

export type VerificationMode = "REFERENCE_CHECK" | "AI_ONLY";

type ModeSelectorProps = {
  mode: VerificationMode;
  disabled: boolean;
  onChange: (mode: VerificationMode) => void;
};

// Memilih alur pemeriksaan dan mengumumkan perubahan secara aksesibel.
export function ModeSelector({ mode, disabled, onChange }: ModeSelectorProps) {
  return (
    <fieldset className="space-y-3" disabled={disabled}>
      <legend className="mb-2 font-semibold">Pilih jenis pemeriksaan</legend>
      <label className="flex cursor-pointer gap-3 rounded-lg border p-3">
        <input type="radio" name="verification-mode" value="REFERENCE_CHECK" checked={mode === "REFERENCE_CHECK"} onChange={() => onChange("REFERENCE_CHECK")} />
        <span><span className="block font-medium">Saya punya kode referensi</span><span className="text-sm text-muted-foreground">Periksa bukti penerbitan; PDF dapat digunakan untuk memeriksa keutuhan berkas.</span></span>
      </label>
      <label className="flex cursor-pointer gap-3 rounded-lg border p-3">
        <input type="radio" name="verification-mode" value="AI_ONLY" checked={mode === "AI_ONLY"} onChange={() => onChange("AI_ONLY")} />
        <span><span className="block font-medium">Saya tidak punya kode referensi</span><span className="text-sm text-muted-foreground">Analisis indikasi risiko dari isi PDF dengan AI.</span></span>
      </label>
    </fieldset>
  );
}
