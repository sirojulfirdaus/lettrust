// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-04.01–FR-04.06, §9.8; SA §10.6 (API-06), §11.2.3
"use client";

import { useEffect, useRef, useState } from "react";
import { AlertCircle, AlertTriangle, Loader2, RefreshCw } from "lucide-react";
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
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  REVOCATION_REASON_OPTIONS,
  getRevocationReasonLabel,
} from "@/components/proofs/proof-status-badge";
import type { RevocationReasonCode, RevokeProofResponse } from "@/lib/api/client";
import {
  generateIdempotencyKey,
  isValidRevocationReasonCode,
  submitRevokeProof,
} from "@/app/hr/proofs/proofs-flow";

type RevokeDialogProps = {
  proofId: string;
  referenceCode: string;
  disabled?: boolean;
  onRevoked: (result: RevokeProofResponse) => void;
  onAlreadyRevoked: (message: string) => void;
  onUnauthorized: () => void;
};

type RevokeErrorState = {
  code: string;
  message: string;
  canRetrySameKey: boolean;
  requiresResetKey: boolean;
};

// Panel dan dialog konfirmasi pencabutan bukti ACTIVE melalui API-06 dengan reasonCode dan Idempotency-Key.
export function RevokeDialog({
  proofId,
  referenceCode,
  disabled = false,
  onRevoked,
  onAlreadyRevoked,
  onUnauthorized,
}: RevokeDialogProps) {
  const [reasonCode, setReasonCode] = useState<RevocationReasonCode>("OFFER_WITHDRAWN");
  const [idempotencyKey, setIdempotencyKey] = useState<string>(() => generateIdempotencyKey());
  const [isAttemptLocked, setIsAttemptLocked] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<RevokeErrorState | null>(null);

  const isSubmittingRef = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const isReasonLocked = isSubmitting || isAttemptLocked || disabled;
  const isActionDisabled = isSubmitting || disabled;

  // Mengirim permintaan pencabutan API-06 dengan penjaga double-submit dan Idempotency-Key tetap saat retry.
  const executeRevoke = async () => {
    if (disabled || isSubmittingRef.current || !isValidRevocationReasonCode(reasonCode)) {
      return;
    }

    isSubmittingRef.current = true;
    setIsSubmitting(true);
    setSubmitError(null);

    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const result = await submitRevokeProof({
      proofId,
      reasonCode,
      idempotencyKey,
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
      setIsAttemptLocked(false);
      onRevoked(result.data);
      return;
    }

    if (result.kind === "already_revoked") {
      setIsAttemptLocked(false);
      onAlreadyRevoked(result.message);
      return;
    }

    setIsAttemptLocked(result.canRetrySameKey);
    setSubmitError({
      code: result.code,
      message: result.message,
      canRetrySameKey: result.canRetrySameKey,
      requiresResetKey: result.requiresResetKey,
    });
  };

  return (
    <Card className="border-status-warning/40">
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2 text-base">
          <AlertTriangle className="size-4 text-status-warning" aria-hidden="true" />
          Cabut Bukti Penerbitan
        </CardTitle>
        <CardDescription>
          Pencabutan bersifat permanen dan tidak dapat dibatalkan. Pilih alasan pencabutan yang
          sesuai sebelum mengonfirmasi tindakan.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        <fieldset className="space-y-3" disabled={isReasonLocked}>
          <legend className="text-sm font-medium text-foreground">Alasan Pencabutan</legend>
          <RadioGroup
            value={reasonCode}
            disabled={isReasonLocked}
            onValueChange={(value) => {
              if (isReasonLocked) {
                return;
              }
              if (isValidRevocationReasonCode(value)) {
                setReasonCode(value);
                setSubmitError(null);
              }
            }}
            className="gap-2.5"
          >
            {REVOCATION_REASON_OPTIONS.map((option) => {
              const optionId = `revoke-reason-${option.code}`;
              return (
                <div
                  key={option.code}
                  className={`flex items-start gap-3 rounded-lg border bg-card p-3 transition-colors ${
                    isReasonLocked ? "opacity-75" : "hover:bg-muted/40"
                  }`}
                >
                  <RadioGroupItem
                    value={option.code}
                    id={optionId}
                    disabled={isReasonLocked}
                    className={`mt-0.5 ${isReasonLocked ? "cursor-not-allowed" : "cursor-pointer"}`}
                  />
                  <Label
                    htmlFor={optionId}
                    className={`flex flex-col items-start gap-0.5 font-normal ${
                      isReasonLocked ? "cursor-not-allowed" : "cursor-pointer"
                    }`}
                  >
                    <span className="text-sm font-medium text-foreground">{option.label}</span>
                    <span className="text-xs text-muted-foreground">{option.description}</span>
                  </Label>
                </div>
              );
            })}
          </RadioGroup>
          {isAttemptLocked ? (
            <p className="text-xs text-muted-foreground">
              Alasan pencabutan dikunci sementara agar percobaan ulang menggunakan kunci idempotensi
              yang sama tetap konsisten dengan permintaan sebelumnya.
            </p>
          ) : null}
        </fieldset>

        {submitError ? (
          <Alert variant="destructive">
            <AlertCircle className="size-4" aria-hidden="true" />
            <AlertTitle>Pencabutan bukti gagal</AlertTitle>
            <AlertDescription className="space-y-3">
              <p>{submitError.message}</p>
              <div className="flex flex-wrap gap-2">
                {submitError.canRetrySameKey ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={isActionDisabled}
                    onClick={() => void executeRevoke()}
                    className={isActionDisabled ? "cursor-not-allowed" : "cursor-pointer"}
                  >
                    <RefreshCw className="size-3.5" aria-hidden="true" />
                    Coba lagi
                  </Button>
                ) : null}
                {submitError.requiresResetKey ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={isActionDisabled}
                    onClick={() => {
                      setIsAttemptLocked(false);
                      setIdempotencyKey(generateIdempotencyKey());
                      setSubmitError(null);
                    }}
                    className={isActionDisabled ? "cursor-not-allowed" : "cursor-pointer"}
                  >
                    Mulai ulang
                  </Button>
                ) : null}
              </div>
            </AlertDescription>
          </Alert>
        ) : null}

        <div className="flex justify-end border-t pt-4">
          <Button
            type="button"
            variant="destructive"
            disabled={isActionDisabled}
            onClick={() => {
              if (!isActionDisabled) {
                setConfirmOpen(true);
              }
            }}
            className={isActionDisabled ? "cursor-not-allowed" : "cursor-pointer"}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                Mencabut bukti...
              </>
            ) : (
              "Cabut Bukti"
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
              <AlertTriangle className="size-5 text-status-warning" aria-hidden="true" />
              Konfirmasi Pencabutan Bukti
            </DialogTitle>
            <DialogDescription>
              Tindakan ini tidak dapat dibatalkan setelah terkonfirmasi di registry.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 text-sm text-foreground">
            <div className="rounded-lg border bg-muted/50 px-3.5 py-2.5 space-y-1">
              <p className="text-xs text-muted-foreground">Kode Referensi</p>
              <p className="font-mono font-semibold text-foreground">{referenceCode}</p>
              <p className="text-xs text-muted-foreground pt-1">
                Alasan: <span className="font-medium text-foreground">{getRevocationReasonLabel(reasonCode)}</span>
              </p>
            </div>
            <p className="text-muted-foreground">
              Setelah bukti dicabut, pelamar yang memverifikasi kode referensi ini akan melihat
              status Dicabut. Bukti yang sudah dicabut tidak dapat diaktifkan kembali.
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
              variant="destructive"
              disabled={isSubmitting}
              onClick={() => void executeRevoke()}
              className={isSubmitting ? "cursor-not-allowed" : "cursor-pointer"}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                  Memproses...
                </>
              ) : (
                "Ya, Cabut Bukti"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
