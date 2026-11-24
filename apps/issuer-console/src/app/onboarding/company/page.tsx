// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.03, §9.8; SA §10.5 (API-01)
"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle, Building2, Info, Loader2 } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  loadOnboardingGuard,
  submitCompanyRegistration,
  type SubmitErrorState,
} from "./onboarding-flow";
import type { CompanyFieldErrors, CompanyFormValues } from "./validation";

type PageLoadState =
  | { status: "loading" }
  | { status: "ready"; displayName: string }
  | { status: "error"; message: string };

// Halaman registrasi perusahaan bagi akun HR yang belum terhubung dengan penerbit.
export default function CompanyOnboardingPage() {
  const router = useRouter();
  const [attempt, setAttempt] = useState(0);
  const [loadState, setLoadState] = useState<PageLoadState>({ status: "loading" });

  const [values, setValues] = useState<CompanyFormValues>({
    companyName: "",
    registrationNumber: "",
    contactEmail: "",
  });
  const [fieldErrors, setFieldErrors] = useState<CompanyFieldErrors>({});
  const [submitError, setSubmitError] = useState<SubmitErrorState | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const submitGuardRef = useRef(false);
  const submitControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    loadOnboardingGuard({
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
      if (result.kind === "error") {
        setLoadState({ status: "error", message: result.message });
        return;
      }
      setLoadState({ status: "ready", displayName: result.displayName });
    });

    return () => {
      controller.abort();
      submitControllerRef.current?.abort();
    };
  }, [attempt, router]);

  // Memuat ulang pemeriksaan profil sesi dari backend.
  const handleRetryProfile = () => {
    setLoadState({ status: "loading" });
    setAttempt((n) => n + 1);
  };

  // Memperbarui nilai input dan menghapus error field terkait saat pengguna mengetik.
  const handleChange = (field: keyof CompanyFormValues, value: string) => {
    setValues((prev) => ({ ...prev, [field]: value }));
    if (fieldErrors[field]) {
      setFieldErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
    if (submitError) {
      setSubmitError(null);
    }
  };

  // Memvalidasi formulir lalu mengirim pendaftaran perusahaan ke API-01 POST /api/v1/issuers.
  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submitGuardRef.current || isSubmitting) {
      return;
    }

    submitGuardRef.current = true;
    const controller = new AbortController();
    submitControllerRef.current = controller;
    setSubmitError(null);
    setIsSubmitting(true);

    try {
      const result = await submitCompanyRegistration(values, {
        signal: controller.signal,
        onUnauthorized: () => router.replace("/login?reason=session_expired"),
      });
      if (result.kind === "aborted" || result.kind === "unauthorized") {
        return;
      }
      if (result.kind === "validation_error") {
        setFieldErrors(result.fieldErrors);
        return;
      }
      if (result.kind === "error") {
        setFieldErrors(result.fieldErrors ?? {});
        setSubmitError(result.submitError);
        return;
      }
      setFieldErrors({});
      router.replace(result.redirectTo);
    } finally {
      submitGuardRef.current = false;
      if (submitControllerRef.current === controller) {
        submitControllerRef.current = null;
      }
      if (!controller.signal.aborted) {
        setIsSubmitting(false);
      }
    }
  };

  if (loadState.status === "loading") {
    return (
      <div
        role="status"
        aria-live="polite"
        className="mx-auto flex max-w-md flex-col items-center justify-center gap-3 py-16 text-center"
      >
        <Loader2 className="size-6 animate-spin text-primary" aria-hidden="true" />
        <p className="text-sm text-muted-foreground">Memeriksa profil dan status afiliasi Anda...</p>
      </div>
    );
  }

  if (loadState.status === "error") {
    return (
      <div className="mx-auto max-w-lg space-y-4 py-8">
        <Alert variant="destructive">
          <AlertCircle className="size-4" aria-hidden="true" />
          <AlertTitle>Profil sesi belum dapat dimuat</AlertTitle>
          <AlertDescription>{loadState.message}</AlertDescription>
        </Alert>
        <div className="flex flex-wrap gap-3">
          <Button type="button" onClick={handleRetryProfile} className="cursor-pointer">
            Coba lagi
          </Button>
          <Button asChild variant="outline" className="cursor-pointer">
            <Link href="/login">Ke halaman Masuk</Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div className="space-y-1.5">
        <div className="flex items-center gap-2 text-primary">
          <Building2 className="size-5" aria-hidden="true" />
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Registrasi Perusahaan
          </h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Halo, {loadState.displayName}. Daftarkan identitas perusahaan Anda untuk melanjutkan ke
          proses verifikasi oleh Administrator.
        </p>
      </div>

      <Alert>
        <Info className="size-4 text-primary" aria-hidden="true" />
        <AlertTitle>Pemberitahuan data sintetis</AlertTitle>
        <AlertDescription>
          Prototipe ini hanya menggunakan data sintetis. Gunakan nama perusahaan, nomor registrasi,
          dan alamat email simulasi (misalnya berakhiran .test) dan jangan memasukkan data asli.
        </AlertDescription>
      </Alert>

      <Card>
        <CardHeader>
          <CardTitle>Data Identitas Penerbit</CardTitle>
          <CardDescription>
            Setelah didaftarkan, status perusahaan Anda akan menjadi Menunggu Verifikasi hingga
            ditinjau Administrator.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} noValidate className="space-y-5">
            {submitError ? (
              <Alert variant="destructive">
                <AlertCircle className="size-4" aria-hidden="true" />
                <AlertTitle>Pendaftaran tidak dapat diproses</AlertTitle>
                <AlertDescription className="space-y-2">
                  <p>{submitError.message}</p>
                  {submitError.showHrLink ? (
                    <p>
                      <Link
                        href="/hr"
                        className="font-medium underline underline-offset-4 hover:text-foreground"
                      >
                        Buka Beranda HR
                      </Link>
                    </p>
                  ) : null}
                </AlertDescription>
              </Alert>
            ) : null}

            <div className="space-y-2">
              <Label htmlFor="companyName">Nama Perusahaan</Label>
              <Input
                id="companyName"
                name="companyName"
                type="text"
                autoComplete="organization"
                required
                minLength={3}
                disabled={isSubmitting}
                value={values.companyName}
                onChange={(event) => handleChange("companyName", event.target.value)}
                placeholder="Contoh: PT Contoh Rekrutmen"
                aria-invalid={Boolean(fieldErrors.companyName)}
                aria-describedby={
                  fieldErrors.companyName ? "companyName-error" : "companyName-hint"
                }
              />
              {fieldErrors.companyName ? (
                <p id="companyName-error" className="text-xs text-destructive">
                  {fieldErrors.companyName}
                </p>
              ) : (
                <p id="companyName-hint" className="text-xs text-muted-foreground">
                  Panjang 3 hingga 120 karakter.
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="registrationNumber">Nomor Registrasi Perusahaan</Label>
              <Input
                id="registrationNumber"
                name="registrationNumber"
                type="text"
                required
                minLength={3}
                disabled={isSubmitting}
                value={values.registrationNumber}
                onChange={(event) => handleChange("registrationNumber", event.target.value)}
                placeholder="Contoh: REG-DEMO-101"
                aria-invalid={Boolean(fieldErrors.registrationNumber)}
                aria-describedby={
                  fieldErrors.registrationNumber
                    ? "registrationNumber-error"
                    : "registrationNumber-hint"
                }
              />
              {fieldErrors.registrationNumber ? (
                <p id="registrationNumber-error" className="text-xs text-destructive">
                  {fieldErrors.registrationNumber}
                </p>
              ) : (
                <p id="registrationNumber-hint" className="text-xs text-muted-foreground">
                  Panjang 3 hingga 40 karakter; hanya huruf, angka, titik (.), garis miring (/), atau
                  tanda hubung (-).
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="contactEmail">Email Kontak Perusahaan</Label>
              <Input
                id="contactEmail"
                name="contactEmail"
                type="email"
                autoComplete="email"
                required
                disabled={isSubmitting}
                value={values.contactEmail}
                onChange={(event) => handleChange("contactEmail", event.target.value)}
                placeholder="Contoh: hr@contoh.test"
                aria-invalid={Boolean(fieldErrors.contactEmail)}
                aria-describedby={
                  fieldErrors.contactEmail ? "contactEmail-error" : "contactEmail-hint"
                }
              />
              {fieldErrors.contactEmail ? (
                <p id="contactEmail-error" className="text-xs text-destructive">
                  {fieldErrors.contactEmail}
                </p>
              ) : (
                <p id="contactEmail-hint" className="text-xs text-muted-foreground">
                  Gunakan alamat email kontak sintetis untuk keperluan verifikasi.
                </p>
              )}
            </div>

            <div className="pt-2">
              <Button
                type="submit"
                size="lg"
                disabled={isSubmitting}
                className="w-full cursor-pointer disabled:cursor-not-allowed sm:w-auto"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                    Mendaftarkan perusahaan...
                  </>
                ) : (
                  "Daftarkan Perusahaan"
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
