// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.02, §9.2, §9.10, §9.11; SA §11.2.1, §11.2.2
"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  fetchSessionProfile,
  registerUnauthorizedHandler,
  type MeResponse,
} from "@/lib/api/client";
import { getNavRoutesForUser } from "@/lib/routes";
import { clearSession, readSession, SESSION_CHANGE_EVENT } from "@/lib/session";

// Berlangganan perubahan sesi pada tab aktif untuk useSyncExternalStore.
function subscribeToSession(callback: () => void): () => void {
  window.addEventListener(SESSION_CHANGE_EVENT, callback);
  return () => window.removeEventListener(SESSION_CHANGE_EVENT, callback);
}

// Mengambil token sesi aktif di browser sebagai snapshot sinkron.
function getSessionTokenSnapshot(): string | null {
  return readSession()?.accessToken ?? null;
}

// Snapshot server selalu null karena sesi hanya ada di sessionStorage browser.
function getServerSessionSnapshot(): string | null {
  return null;
}

// Header Console dengan identitas aplikasi, penanda data sintetis, navigasi berbasis peran, dan tombol keluar.
export function ConsoleHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const accessToken = useSyncExternalStore(
    subscribeToSession,
    getSessionTokenSnapshot,
    getServerSessionSnapshot,
  );
  const [profileState, setProfileState] = useState<{
    token: string;
    profile: MeResponse;
  } | null>(null);

  useEffect(() => {
    return registerUnauthorizedHandler(() => {
      if (pathname !== "/login") {
        router.replace("/login?reason=session_expired");
      }
    });
  }, [pathname, router]);

  useEffect(() => {
    if (!accessToken) {
      return;
    }

    const controller = new AbortController();
    fetchSessionProfile({ signal: controller.signal })
      .then((me) => {
        if (!controller.signal.aborted) {
          setProfileState({ token: accessToken, profile: me });
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setProfileState(null);
        }
      });

    return () => controller.abort();
  }, [accessToken, pathname]);

  const hasSession = accessToken !== null;
  const profile =
    hasSession && profileState && profileState.token === accessToken
      ? profileState.profile
      : null;

  const handleLogout = () => {
    clearSession();
    setProfileState(null);
    router.replace("/login");
  };

  const navRoutes = profile ? getNavRoutesForUser(profile) : [];

  return (
    <header className="border-b bg-card">
      <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center gap-4 px-4 py-3">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="font-heading text-lg font-bold text-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
          >
            Lettrust Console
          </Link>
          <Badge variant="outline">Data sintetis</Badge>
        </div>

        <nav aria-label="Navigasi utama" className="ml-auto flex flex-wrap items-center gap-2 text-sm">
          {hasSession && profile ? (
            <>
              {navRoutes.map((route) => {
                const isActive =
                  route.path === "/hr/proofs"
                    ? pathname === "/hr/proofs" ||
                      (pathname.startsWith("/hr/proofs/") && pathname !== "/hr/proofs/new")
                    : pathname === route.path ||
                      (route.path !== "/hr" && pathname.startsWith(`${route.path}/`));
                return (
                  <Link
                    key={route.path}
                    href={route.path}
                    aria-current={isActive ? "page" : undefined}
                    className={`rounded-md px-3 py-1.5 font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ${
                      isActive
                        ? "bg-primary/10 text-primary"
                        : "text-foreground/80 hover:bg-muted hover:text-foreground"
                    }`}
                  >
                    {route.title}
                  </Link>
                );
              })}

              <div className="ml-2 flex items-center gap-3 border-l pl-3">
                <div className="hidden text-right leading-tight sm:block">
                  <p className="text-xs font-medium text-foreground">{profile.displayName}</p>
                  <p className="text-xs text-muted-foreground">
                    {profile.role === "ADMIN" ? "Administrator" : "HR Penerbit"}
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleLogout}
                  className="cursor-pointer"
                >
                  <LogOut className="size-3.5" aria-hidden="true" />
                  Keluar
                </Button>
              </div>
            </>
          ) : hasSession ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleLogout}
              className="cursor-pointer"
            >
              <LogOut className="size-3.5" aria-hidden="true" />
              Keluar
            </Button>
          ) : (
            <>
              <Link
                href="/login"
                aria-current={pathname === "/login" ? "page" : undefined}
                className={`rounded-md px-3 py-1.5 font-medium transition-colors ${
                  pathname === "/login"
                    ? "bg-primary/10 text-primary"
                    : "text-foreground/80 hover:bg-muted hover:text-foreground"
                }`}
              >
                Masuk
              </Link>
              <Link
                href="/register"
                aria-current={pathname === "/register" ? "page" : undefined}
                className={`rounded-md px-3 py-1.5 font-medium transition-colors ${
                  pathname === "/register"
                    ? "bg-primary/10 text-primary"
                    : "text-foreground/80 hover:bg-muted hover:text-foreground"
                }`}
              >
                Registrasi Akun
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
