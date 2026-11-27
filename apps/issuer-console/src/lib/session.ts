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

// Mencatat token terakhir yang terhapus karena kedaluwarsa per instance Storage
// agar respons 401 tertunda untuk sesi tersebut tetap dibedakan dari logout manual.
const expiredTokenByStorage = new WeakMap<Storage, string>();

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

// Memberi tahu komponen klien bahwa status sesi atau profilnya berubah (mis. setelah afiliasi perusahaan baru).
export function notifySessionChange(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new Event(SESSION_CHANGE_EVENT));
}

// Membaca objek sesi mentah dari storage tanpa menghapusnya bila kedaluwarsa.
function readStoredSessionRaw(storage: Storage): Session | null {
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

    if (!session.accessToken.trim()) {
      storage.removeItem(SESSION_STORAGE_KEY);
      return null;
    }

    return session;
  } catch {
    storage.removeItem(SESSION_STORAGE_KEY);
    return null;
  }
}

// Membaca sesi aktif; mengembalikan null dan membersihkan storage bila tidak ada, rusak, atau kedaluwarsa.
export function readSession(nowMs: number = Date.now()): Session | null {
  const storage = getStorage();
  if (!storage) {
    return null;
  }

  const session = readStoredSessionRaw(storage);
  if (!session) {
    return null;
  }

  if (isSessionExpired(session, nowMs)) {
    expiredTokenByStorage.set(storage, session.accessToken);
    storage.removeItem(SESSION_STORAGE_KEY);
    return null;
  }

  return session;
}

// Tujuan redirect ke login saat readSession() kosong (FR-01.02 AC-05).
export type LoginRedirectPath = "/login" | "/login?reason=session_expired";

// Membedakan sesi yang baru kedaluwarsa (ditandai readSession) dari tidak ada sesi sama sekali.
export function sessionRedirectPath(): LoginRedirectPath {
  const storage = getStorage();
  return storage && expiredTokenByStorage.has(storage) ? "/login?reason=session_expired" : "/login";
}

// Menyimpan sesi hasil login ke sessionStorage.
export function saveSession(session: Session): void {
  const storage = getStorage();
  if (!storage) {
    return;
  }
  expiredTokenByStorage.delete(storage);
  storage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
  notifySessionChange();
}

// Menghapus sesi secara eksplisit (logout atau pembersihan setelah 401).
export function clearSession(): void {
  const storage = getStorage();
  if (!storage) {
    return;
  }
  expiredTokenByStorage.delete(storage);
  storage.removeItem(SESSION_STORAGE_KEY);
  notifySessionChange();
}

// Memutuskan apakah respons 401 untuk sentToken masih relevan dengan sesi aktif atau sesi yang baru kedaluwarsa,
// sekaligus membersihkan sesi bila relevan; mengembalikan false jika sesi sudah diganti atau di-logout manual.
export function consumeUnauthorizedSession(sentToken: string | null): boolean {
  const storage = getStorage();
  if (!storage) {
    return sentToken === null;
  }

  const stored = readStoredSessionRaw(storage);
  if (stored !== null) {
    if (stored.accessToken !== sentToken) {
      return false;
    }
    clearSession();
    return true;
  }

  if (sentToken === null) {
    if (expiredTokenByStorage.delete(storage)) {
      notifySessionChange();
    }
    return true;
  }

  if (expiredTokenByStorage.get(storage) === sentToken) {
    expiredTokenByStorage.delete(storage);
    notifySessionChange();
    return true;
  }

  return false;
}
