// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.01, §9.8; SA §10.5 (S-01)
"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle, Info, Loader2 } from "lucide-react";
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
import { submitRegisterFlow } from "@/app/login/auth-flow";
import {
  mapValidationDetails,
  validateRegisterForm,
  type RegisterFieldErrors,
} from "@/app/login/auth-validation";

// Halaman Registrasi Akun HR (FR-01.01); akun baru selalu ber-role HR tanpa pilihan role di client.
export default function RegisterPage() {
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<RegisterFieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [emailRegisteredConflict, setEmailRegisteredConflict] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);
    setEmailRegisteredConflict(false);

    const validation = validateRegisterForm(displayName, email, password);
    setFieldErrors(validation);
    if (Object.keys(validation).length > 0) {
      return;
    }

    setIsSubmitting(true);
    try {
      await submitRegisterFlow(displayName, email, password);
      router.replace("/login?registered=1");
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.code === "VALIDATION_ERROR" && error.details.length > 0) {
          setFieldErrors(mapValidationDetails(error.details));
        }
        if (error.code === "EMAIL_ALREADY_REGISTERED") {
          setEmailRegisteredConflict(true);
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
      <Card>
        <CardHeader>
          <CardTitle className="font-heading text-xl">Registrasi Akun HR</CardTitle>
          <CardDescription>
            Buat akun perwakilan perusahaan (HR). Setelah masuk, Anda dapat mendaftarkan perusahaan
            untuk ditinjau Administrator.
          </CardDescription>
        </CardHeader>

        <form onSubmit={(e) => void handleSubmit(e)} noValidate>
          <CardContent className="space-y-4">
            <Alert>
              <Info className="size-4 text-primary" aria-hidden="true" />
              <AlertTitle>Pemberitahuan data sintetis</AlertTitle>
              <AlertDescription>
                Prototipe ini hanya menggunakan data sintetis. Gunakan nama, email, dan password
                fiktif untuk pengujian lokal.
              </AlertDescription>
            </Alert>

            {formError && (
              <Alert variant="destructive">
                <AlertCircle className="size-4" aria-hidden="true" />
                <AlertTitle>Registrasi gagal</AlertTitle>
                <AlertDescription>
                  {formError}
                  {emailRegisteredConflict && (
                    <>
                      {" "}
                      <Link href="/login" className="font-medium underline">
                        Ke halaman Masuk
                      </Link>
                    </>
                  )}
                </AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="register-display-name">Nama lengkap</Label>
              <Input
                id="register-display-name"
                name="displayName"
                type="text"
                autoComplete="name"
                placeholder="Rina Demo"
                value={displayName}
                onChange={(e) => {
                  setDisplayName(e.target.value);
                  if (fieldErrors.displayName) {
                    setFieldErrors((prev) => ({ ...prev, displayName: undefined }));
                  }
                }}
                aria-invalid={Boolean(fieldErrors.displayName)}
                aria-describedby={
                  fieldErrors.displayName ? "register-name-error" : "register-name-hint"
                }
                disabled={isSubmitting}
                required
              />
              {fieldErrors.displayName ? (
                <p id="register-name-error" className="text-xs text-destructive">
                  {fieldErrors.displayName}
                </p>
              ) : (
                <p id="register-name-hint" className="text-xs text-muted-foreground">
                  2–80 karakter.
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="register-email">Email</Label>
              <Input
                id="register-email"
                name="email"
                type="email"
                autoComplete="email"
                placeholder="rina@lettrust.test"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (fieldErrors.email) {
                    setFieldErrors((prev) => ({ ...prev, email: undefined }));
                  }
                }}
                aria-invalid={Boolean(fieldErrors.email)}
                aria-describedby={fieldErrors.email ? "register-email-error" : undefined}
                disabled={isSubmitting}
                required
              />
              {fieldErrors.email && (
                <p id="register-email-error" className="text-xs text-destructive">
                  {fieldErrors.email}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="register-password">Password</Label>
              <Input
                id="register-password"
                name="password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (fieldErrors.password) {
                    setFieldErrors((prev) => ({ ...prev, password: undefined }));
                  }
                }}
                aria-invalid={Boolean(fieldErrors.password)}
                aria-describedby={
                  fieldErrors.password ? "register-password-error" : "register-password-hint"
                }
                disabled={isSubmitting}
                required
              />
              {fieldErrors.password ? (
                <p id="register-password-error" className="text-xs text-destructive">
                  {fieldErrors.password}
                </p>
              ) : (
                <p id="register-password-hint" className="text-xs text-muted-foreground">
                  Minimal 8 karakter (maksimal 128 karakter).
                </p>
              )}
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
                  Mendaftarkan...
                </>
              ) : (
                "Daftar Akun HR"
              )}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              Sudah memiliki akun?{" "}
              <Link href="/login" className="font-medium text-primary hover:underline">
                Masuk
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
