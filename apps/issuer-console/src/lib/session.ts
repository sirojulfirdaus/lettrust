// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.02; SA §11.2.2, TOI-13

// Kunci sessionStorage untuk sesi Console (bukan localStorage atau cookie).
export const SESSION_STORAGE_KEY = "lettrust.session";

// Nama event browser saat sesi berubah agar header dan guard sinkron dalam tab yang sama.
export const SESSION_CHANGE_EVENT = "lettrust:session-change";

// Bentuk sesi yang disimpan setelah login S-02.
export type Session = {
  accessToken: string;
  expiresAt: string;
};

// Membentuk objek sesi dari token dan masa berlaku (detik) respons S-02.
export function createSession(
  accessToken: string,
  expiresInSeconds: number,
  nowMs: number = Date.now(),
): Session {
  const expiresAt = new Date(nowMs + expiresInSeconds * 1000).toISOString();
  return { accessToken, expiresAt };
}

// Memeriksa apakah waktu kedaluwarsa sesi sudah lewat atau tidak valid.
export function isSessionExpired(session: Session, nowMs: number = Date.now()): boolean {
  const parsed = Date.parse(session.expiresAt);
  if (Number.isNaN(parsed)) {
    return true;
  }
  return parsed <= nowMs;
}

// Mengakses sessionStorage dengan aman saat kode dijalankan di lingkungan server (SSR).
function getStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

// Memberi tahu komponen klien bahwa status sesi telah berubah.
function notifySessionChange(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new Event(SESSION_CHANGE_EVENT));
}

// Membaca sesi aktif; mengembalikan null dan membersihkan storage bila tidak ada, rusak, atau kedaluwarsa.
export function readSession(nowMs: number = Date.now()): Session | null {
  const storage = getStorage();
  if (!storage) {
    return null;
  }

  const raw = storage.getItem(SESSION_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    const parsed: unknown = JSON.parse(raw);
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      typeof (parsed as Record<string, unknown>).accessToken !== "string" ||
      typeof (parsed as Record<string, unknown>).expiresAt !== "string"
    ) {
      storage.removeItem(SESSION_STORAGE_KEY);
      return null;
    }

    const session: Session = {
      accessToken: (parsed as Record<string, string>).accessToken,
      expiresAt: (parsed as Record<string, string>).expiresAt,
    };

    if (!session.accessToken.trim() || isSessionExpired(session, nowMs)) {
      storage.removeItem(SESSION_STORAGE_KEY);
      return null;
    }

    return session;
  } catch {
    storage.removeItem(SESSION_STORAGE_KEY);
    return null;
  }
}

// Menyimpan sesi hasil login ke sessionStorage.
export function saveSession(session: Session): void {
  const storage = getStorage();
  if (!storage) {
    return;
  }
  storage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
  notifySessionChange();
}

// Menghapus sesi (logout atau respons 401).
export function clearSession(): void {
  const storage = getStorage();
  if (!storage) {
    return;
  }
  storage.removeItem(SESSION_STORAGE_KEY);
  notifySessionChange();
}
