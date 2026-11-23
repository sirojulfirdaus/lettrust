// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.02, §9.3.1, §9.8; SA §10.5 (S-02, S-03), §11.2.2
"use client";

import { Suspense, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertCircle, CheckCircle2, Info, Loader2 } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api/client";
import { submitLoginFlow } from "./auth-flow";
import {
  mapValidationDetails,
  validateLoginForm,
  type LoginFieldErrors,
} from "./auth-validation";

// Formulir login klien yang membaca query string (alasan sesi berakhir atau registrasi baru).
function LoginFormContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionExpired = searchParams.get("reason") === "session_expired";
  const justRegistered = searchParams.get("registered") === "1";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<LoginFieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);

    const validation = validateLoginForm(email, password);
    setFieldErrors(validation);
    if (Object.keys(validation).length > 0) {
      return;
    }

    setIsSubmitting(true);
    try {
      const { redirectTo } = await submitLoginFlow(email, password);
      router.replace(redirectTo);
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.code === "VALIDATION_ERROR" && error.details.length > 0) {
          const mapped = mapValidationDetails(error.details);
          setFieldErrors({ email: mapped.email, password: mapped.password });
        }
        setFormError(error.message);
      } else {
        setFormError("Layanan sedang tidak tersedia. Coba lagi beberapa saat lagi.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-md space-y-4">
      {sessionExpired && (
        <Alert variant="destructive">
          <AlertCircle className="size-4" aria-hidden="true" />
          <AlertTitle>Sesi berakhir</AlertTitle>
          <AlertDescription>Sesi Anda telah berakhir. Silakan masuk kembali.</AlertDescription>
        </Alert>
      )}

      {justRegistered && (
        <Alert>
          <CheckCircle2 className="size-4 text-status-positive" aria-hidden="true" />
          <AlertTitle>Registrasi berhasil</AlertTitle>
          <AlertDescription>
            Akun HR berhasil dibuat. Silakan masuk dengan email dan password Anda.
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="font-heading text-xl">Masuk ke Lettrust Console</CardTitle>
          <CardDescription>
            Masuk sebagai HR penerbit atau Administrator untuk mengelola penerbit dan bukti offer
            letter.
          </CardDescription>
        </CardHeader>

        <form onSubmit={(e) => void handleSubmit(e)} noValidate>
          <CardContent className="space-y-4">
            {formError && (
              <Alert variant="destructive">
                <AlertCircle className="size-4" aria-hidden="true" />
                <AlertTitle>Gagal masuk</AlertTitle>
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="login-email">Email</Label>
              <Input
                id="login-email"
                name="email"
                type="email"
                autoComplete="email"
                placeholder="nama@perusahaan.test"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (fieldErrors.email) {
                    setFieldErrors((prev) => ({ ...prev, email: undefined }));
                  }
                }}
                aria-invalid={Boolean(fieldErrors.email)}
                aria-describedby={fieldErrors.email ? "login-email-error" : undefined}
                disabled={isSubmitting}
                required
              />
              {fieldErrors.email && (
                <p id="login-email-error" className="text-xs text-destructive">
                  {fieldErrors.email}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="login-password">Password</Label>
              <Input
                id="login-password"
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (fieldErrors.password) {
                    setFieldErrors((prev) => ({ ...prev, password: undefined }));
                  }
                }}
                aria-invalid={Boolean(fieldErrors.password)}
                aria-describedby={fieldErrors.password ? "login-password-error" : undefined}
                disabled={isSubmitting}
                required
              />
              {fieldErrors.password && (
                <p id="login-password-error" className="text-xs text-destructive">
                  {fieldErrors.password}
                </p>
              )}
            </div>

            <div className="flex items-start gap-2 rounded-md border bg-muted/50 p-3 text-xs text-muted-foreground">
              <Info className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
              <p>
                Prototipe akademik ini hanya menggunakan data sintetis. Jangan masukkan kredensial
                atau data pribadi nyata.
              </p>
            </div>
          </CardContent>

          <CardFooter className="flex flex-col items-stretch gap-3 pt-4">
            <Button
              type="submit"
              disabled={isSubmitting}
              className="w-full cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                  Memproses...
                </>
              ) : (
                "Masuk"
              )}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              Belum memiliki akun HR?{" "}
              <Link href="/register" className="font-medium text-primary hover:underline">
                Registrasi Akun
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}

// Halaman Login Console (FR-01.02).
export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div
          role="status"
          className="mx-auto flex max-w-md items-center justify-center gap-2 py-16 text-sm text-muted-foreground"
        >
          <Loader2 className="size-5 animate-spin text-primary" aria-hidden="true" />
          Memuat halaman masuk...
        </div>
      }
    >
      <LoginFormContent />
    </Suspense>
  );
}
