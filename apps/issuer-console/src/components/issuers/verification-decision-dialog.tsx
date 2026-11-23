// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.05, §9.8; SA §10.5 (API-02)
"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, CheckCircle2, Loader2, ShieldCheck, XCircle } from "lucide-react";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Textarea } from "@/components/ui/textarea";
import {
  submitVerificationDecision,
  validateVerificationDecisionInput,
  type IssuerDecision,
} from "@/app/admin/issuers/admin-issuers-flow";

interface VerificationDecisionDialogProps {
  issuerId: string;
  companyName: string;
  onSuccess: () => void;
}

// Panel keputusan verifikasi penerbit dengan validasi input dan dialog konfirmasi sebelum mengirim API-02.
export function VerificationDecisionDialog({
  issuerId,
  companyName,
  onSuccess,
}: VerificationDecisionDialogProps) {
  const router = useRouter();
  const [decision, setDecision] = useState<IssuerDecision>("VERIFIED");
  const [evidenceRef, setEvidenceRef] = useState("");
  const [reviewNote, setReviewNote] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{
    evidenceRefError?: string;
    reviewNoteError?: string;
  }>({});
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const submitGuardRef = useRef(false);

  const handleOpenConfirm = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);

    const validation = validateVerificationDecisionInput({
      decision,
      evidenceRef,
      reviewNote,
    });
    setFieldErrors(validation);

    if (validation.evidenceRefError || validation.reviewNoteError) {
      return;
    }

    setConfirmOpen(true);
  };

  const handleConfirmSubmit = async () => {
    if (submitGuardRef.current) {
      return;
    }
    submitGuardRef.current = true;
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const result = await submitVerificationDecision({
        issuerId,
        decision,
        evidenceRef,
        reviewNote,
        onUnauthorized: () => router.replace("/login?reason=session_expired"),
      });

      if (result.kind === "redirect") {
        router.replace(result.to);
        return;
      }
      if (result.kind === "aborted" || result.kind === "unauthorized") {
        return;
      }
      if (result.kind === "error") {
        setSubmitError(result.message);
        setConfirmOpen(false);
        if (result.code === "ISSUER_DECISION_ALREADY_MADE") {
          onSuccess();
        }
        return;
      }

      setConfirmOpen(false);
      onSuccess();
    } finally {
      submitGuardRef.current = false;
      setIsSubmitting(false);
    }
  };

  const decisionLabel = decision === "VERIFIED" ? "Setujui Verifikasi" : "Tolak Verifikasi";

  return (
    <Card>
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2 text-lg">
          <ShieldCheck className="size-5 text-primary" aria-hidden="true" />
          <span>Keputusan Verifikasi Penerbit</span>
        </CardTitle>
        <CardDescription>
          Tinjau pengajuan perusahaan lalu simpan keputusan verifikasi. Keputusan bersifat final.
        </CardDescription>
      </CardHeader>

      <CardContent className="pt-6">
        <form onSubmit={handleOpenConfirm} className="space-y-5" noValidate>
          {submitError ? (
            <Alert variant="destructive">
              <AlertCircle className="size-4" aria-hidden="true" />
              <AlertTitle>Gagal menyimpan keputusan</AlertTitle>
              <AlertDescription>{submitError}</AlertDescription>
            </Alert>
          ) : null}

          <div className="space-y-2.5">
            <Label>Keputusan Verifikasi</Label>
            <RadioGroup
              value={decision}
              onValueChange={(value) => setDecision(value as IssuerDecision)}
              className="grid gap-3 sm:grid-cols-2"
            >
              <label
                htmlFor="decision-verified"
                className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3.5 transition-colors ${
                  decision === "VERIFIED"
                    ? "border-primary bg-primary/5"
                    : "border-border hover:bg-muted/40"
                }`}
              >
                <RadioGroupItem id="decision-verified" value="VERIFIED" className="mt-0.5" />
                <div className="space-y-0.5">
                  <span className="flex items-center gap-1.5 text-sm font-medium text-foreground">
                    <CheckCircle2 className="size-4 text-status-positive" aria-hidden="true" />
                    Verifikasi (VERIFIED)
                  </span>
                  <p className="text-xs text-muted-foreground">
                    Perusahaan dinyatakan terverifikasi dan siap untuk otorisasi HR.
                  </p>
                </div>
              </label>

              <label
                htmlFor="decision-rejected"
                className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3.5 transition-colors ${
                  decision === "REJECTED"
                    ? "border-destructive bg-destructive/5"
                    : "border-border hover:bg-muted/40"
                }`}
              >
                <RadioGroupItem id="decision-rejected" value="REJECTED" className="mt-0.5" />
                <div className="space-y-0.5">
                  <span className="flex items-center gap-1.5 text-sm font-medium text-foreground">
                    <XCircle className="size-4 text-status-danger" aria-hidden="true" />
                    Tolak (REJECTED)
                  </span>
                  <p className="text-xs text-muted-foreground">
                    Pengajuan perusahaan ditolak disertai referensi bukti dan catatan.
                  </p>
                </div>
              </label>
            </RadioGroup>
          </div>

          <div className="space-y-2">
            <Label htmlFor="evidenceRef">Referensi Bukti (3–120 karakter)</Label>
            <Input
              id="evidenceRef"
              name="evidenceRef"
              value={evidenceRef}
              onChange={(event) => {
                setEvidenceRef(event.target.value);
                if (fieldErrors.evidenceRefError) {
                  setFieldErrors((prev) => ({ ...prev, evidenceRefError: undefined }));
                }
              }}
              placeholder="Contoh: EVD-DEMO-003"
              aria-invalid={Boolean(fieldErrors.evidenceRefError)}
              aria-describedby={fieldErrors.evidenceRefError ? "evidenceRef-error" : undefined}
              disabled={isSubmitting}
            />
            {fieldErrors.evidenceRefError ? (
              <p id="evidenceRef-error" className="text-xs text-destructive">
                {fieldErrors.evidenceRefError}
              </p>
            ) : null}
          </div>

          <div className="space-y-2">
            <Label htmlFor="reviewNote">Catatan Peninjauan (opsional, maks. 500 karakter)</Label>
            <Textarea
              id="reviewNote"
              name="reviewNote"
              rows={3}
              value={reviewNote}
              onChange={(event) => {
                setReviewNote(event.target.value);
                if (fieldErrors.reviewNoteError) {
                  setFieldErrors((prev) => ({ ...prev, reviewNoteError: undefined }));
                }
              }}
              placeholder="Catatan tambahan untuk tim HR atau jejak audit internal"
              aria-invalid={Boolean(fieldErrors.reviewNoteError)}
              aria-describedby={fieldErrors.reviewNoteError ? "reviewNote-error" : undefined}
              disabled={isSubmitting}
            />
            {fieldErrors.reviewNoteError ? (
              <p id="reviewNote-error" className="text-xs text-destructive">
                {fieldErrors.reviewNoteError}
              </p>
            ) : null}
          </div>

          <div className="flex justify-end">
            <Button type="submit" disabled={isSubmitting} className="cursor-pointer">
              Tinjau &amp; Konfirmasi Keputusan
            </Button>
          </div>
        </form>
      </CardContent>

      <Dialog open={confirmOpen} onOpenChange={(open) => !isSubmitting && setConfirmOpen(open)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Konfirmasi {decisionLabel}</DialogTitle>
            <DialogDescription>
              Anda akan menyimpan keputusan{" "}
              <span className="font-semibold text-foreground">{decision}</span> untuk{" "}
              <span className="font-semibold text-foreground">{companyName}</span>. Tindakan ini
              tidak dapat diubah setelah disimpan.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-2 rounded-lg border bg-muted/40 p-3.5 text-sm">
            <div className="flex justify-between gap-3">
              <span className="text-muted-foreground">Referensi Bukti:</span>
              <span className="font-mono font-medium text-foreground">{evidenceRef.trim()}</span>
            </div>
            <div className="space-y-1">
              <span className="text-muted-foreground">Catatan Peninjauan:</span>
              <p className="whitespace-pre-wrap text-foreground">
                {reviewNote.trim().length > 0 ? reviewNote.trim() : "-"}
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setConfirmOpen(false)}
              disabled={isSubmitting}
              className="cursor-pointer"
            >
              Batal
            </Button>
            <Button
              type="button"
              variant={decision === "REJECTED" ? "destructive" : "default"}
              onClick={handleConfirmSubmit}
              disabled={isSubmitting}
              className="cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                  Menyimpan...
                </>
              ) : (
                `Ya, ${decisionLabel}`
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
