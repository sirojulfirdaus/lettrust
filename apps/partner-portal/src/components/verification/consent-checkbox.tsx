// Owner: Pash (PIC 4) | Status: COMPLETE | Ref: PRD FR-02.06, BR-04.10, BR-05.04
"use client";

import { Checkbox } from "@/components/ui/checkbox";
import { getAiConsentText } from "@/lib/verification/consent";

type ConsentCheckboxProps = {
  checked: boolean;
  disabled?: boolean;
  onCheckedChange: (checked: boolean) => void;
  // Menandai persetujuan yang ditolak validasi dan menghubungkannya ke pesan error (aksesibilitas).
  invalid?: boolean;
  describedBy?: string;
};

// Meminta persetujuan eksplisit untuk satu kali analisis AI; kotak centang sejajar baris pertama teks.
export function ConsentCheckbox({ checked, disabled, onCheckedChange, invalid, describedBy }: ConsentCheckboxProps) {
  return (
    <label className="flex items-start gap-3 rounded-lg border p-3 text-sm">
      <Checkbox className="mt-0.5" checked={checked} disabled={disabled} onCheckedChange={(value) => onCheckedChange(value === true)} aria-label={getAiConsentText()} aria-invalid={invalid || undefined} aria-describedby={describedBy} />
      <span>{getAiConsentText()}</span>
    </label>
  );
}
