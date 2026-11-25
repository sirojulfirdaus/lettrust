// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.06, §9.8; SA §10.5 (API-03)
"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, CheckCircle2, Loader2, UserCheck, Users } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  submitHrAuthorization,
  validateAuthorizeHrId,
  type IssuerStatus,
} from "@/app/admin/issuers/admin-issuers-flow";
import type { IssuerDetailResponse } from "@/lib/api/client";
import { formatIssuerTimestamp, HrAuthorizationBadge } from "./issuer-status-badge";

interface HrAuthorizationPanelProps {
  issuerId: string;
  issuerStatus: IssuerStatus;
  members: IssuerDetailResponse["members"];
  onAuthorized: () => void;
}

// Panel daftar anggota HR terafiliasi dan form otorisasi HR (API-03) dengan penanganan error §9.8 termasuk 422 HR_NOT_AFFILIATED.
export function HrAuthorizationPanel({
  issuerId,
  issuerStatus,
  members,
  onAuthorized,
}: HrAuthorizationPanelProps) {
  const router = useRouter();
  const [manualHrId, setManualHrId] = useState("");
  const [manualFieldError, setManualFieldError] = useState<string | null>(null);
  const [submittingHrId, setSubmittingHrId] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authSuccess, setAuthSuccess] = useState<string | null>(null);
  const submitGuardRef = useRef(false);

  const canAuthorize = issuerStatus === "VERIFIED";

  const executeAuthorization = async (targetHrId: string, clearManualInput: boolean) => {
    if (submitGuardRef.current) {
      return;
    }
    submitGuardRef.current = true;
    setSubmittingHrId(targetHrId);
    setAuthError(null);
    setAuthSuccess(null);

    try {
      const result = await submitHrAuthorization({
        issuerId,
        hrId: targetHrId,
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
        setAuthError(result.message);
        if (result.code === "HR_ALREADY_AUTHORIZED") {
          onAuthorized();
        }
        return;
      }

      if (clearManualInput) {
        setManualHrId("");
      }
      setAuthSuccess(`Akun HR ${result.data.hrId} berhasil diotorisasi.`);
      onAuthorized();
    } finally {
      submitGuardRef.current = false;
      setSubmittingHrId(null);
    }
  };

  const handleManualSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuthError(null);
    setAuthSuccess(null);

    const validationError = validateAuthorizeHrId(manualHrId);
    setManualFieldError(validationError);
    if (validationError) {
      return;
    }

    await executeAuthorization(manualHrId.trim(), true);
  };

  return (
    <Card>
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Users className="size-5 text-primary" aria-hidden="true" />
          <span>Anggota HR &amp; Otorisasi</span>
        </CardTitle>
        <CardDescription>
          Kelola otorisasi akun HR yang terhubung dengan perusahaan ini untuk penerbitan bukti.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-5 pt-6">
        {!canAuthorize ? (
          <Alert>
            <AlertCircle className="size-4" aria-hidden="true" />
            <AlertTitle>Otorisasi HR belum tersedia</AlertTitle>
            <AlertDescription>
              Penerbit belum terverifikasi sehingga HR belum dapat diotorisasi.
            </AlertDescription>
          </Alert>
        ) : null}

        {authError ? (
          <Alert variant="destructive">
            <AlertCircle className="size-4" aria-hidden="true" />
            <AlertTitle>Gagal mengotorisasi HR</AlertTitle>
            <AlertDescription>{authError}</AlertDescription>
          </Alert>
        ) : null}

        {authSuccess ? (
          <Alert>
            <CheckCircle2 className="size-4 text-status-positive" aria-hidden="true" />
            <AlertTitle>Otorisasi berhasil</AlertTitle>
            <AlertDescription>{authSuccess}</AlertDescription>
          </Alert>
        ) : null}

        {members.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Belum ada akun HR yang terdaftar pada penerbit ini.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nama</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>ID HR</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Diotorisasi</TableHead>
                <TableHead className="text-right">Tindakan</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {members.map((member) => {
                const isThisSubmitting = submittingHrId === member.hrId;
                const isAnySubmitting = submittingHrId !== null;
                return (
                  <TableRow key={member.hrId}>
                    <TableCell className="font-medium">{member.displayName}</TableCell>
                    <TableCell className="text-muted-foreground">{member.email ?? "-"}</TableCell>
                    <TableCell className="font-mono text-xs">{member.hrId}</TableCell>
                    <TableCell>
                      <HrAuthorizationBadge status={member.authorizationStatus} />
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatIssuerTimestamp(member.authorizedAt)}
                    </TableCell>
                    <TableCell className="text-right">
                      {member.authorizationStatus === "NOT_AUTHORIZED" ? (
                        <Button
                          type="button"
                          size="sm"
                          disabled={!canAuthorize || isAnySubmitting}
                          onClick={() => void executeAuthorization(member.hrId, false)}
                          className="cursor-pointer"
                        >
                          {isThisSubmitting ? (
                            <>
                              <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
                              Memproses...
                            </>
                          ) : (
                            <>
                              <UserCheck className="size-3.5" aria-hidden="true" />
                              Otorisasi HR
                            </>
                          )}
                        </Button>
                      ) : (
                        <span className="text-xs text-muted-foreground">Sudah diotorisasi</span>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}

        <form
          onSubmit={handleManualSubmit}
          className="space-y-3 rounded-lg border bg-muted/30 p-4"
          noValidate
        >
          <div className="space-y-1">
            <Label htmlFor="manual-hr-id">Otorisasi berdasarkan ID HR</Label>
            <p className="text-xs text-muted-foreground">
              Masukkan ID akun HR yang telah terhubung dengan penerbit ini (contoh: USR-9R4T6V8W).
            </p>
          </div>
          <div className="flex flex-col gap-2.5 sm:flex-row sm:items-start">
            <div className="flex-1 space-y-1">
              <Input
                id="manual-hr-id"
                name="hrId"
                value={manualHrId}
                onChange={(event) => {
                  setManualHrId(event.target.value);
                  if (manualFieldError) {
                    setManualFieldError(null);
                  }
                }}
                placeholder="USR-..."
                aria-invalid={Boolean(manualFieldError)}
                aria-describedby={manualFieldError ? "manual-hr-id-error" : undefined}
                disabled={!canAuthorize || submittingHrId !== null}
                className="font-mono text-sm"
              />
              {manualFieldError ? (
                <p id="manual-hr-id-error" className="text-xs text-destructive">
                  {manualFieldError}
                </p>
              ) : null}
            </div>
            <Button
              type="submit"
              variant="outline"
              disabled={!canAuthorize || submittingHrId !== null}
              className="cursor-pointer"
            >
              {submittingHrId !== null && submittingHrId === manualHrId.trim() ? (
                <>
                  <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                  Memproses...
                </>
              ) : (
                "Otorisasi"
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
