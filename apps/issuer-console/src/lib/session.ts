// Owner: Van (PIC 2) | Status: STUB | Ref: PRD FR-01.02; SA §11.2.2, TOI-13
// TODO: Implementasi baca/simpan/hapus sesi di sessionStorage ("lettrust.session") dan cek kedaluwarsa expiresAt.

// Kunci sessionStorage untuk sesi Console (bukan localStorage atau cookie).
export const SESSION_STORAGE_KEY = "lettrust.session";

// Bentuk sesi yang disimpan setelah login S-02.
export type Session = {
  accessToken: string;
  expiresAt: string;
};

// Membaca sesi aktif; mengembalikan null bila tidak ada atau sudah kedaluwarsa.
export function readSession(): Session | null {
  throw new Error("NOT_IMPLEMENTED");
}

// Menyimpan sesi hasil login ke sessionStorage.
export function saveSession(_session: Session): void {
  throw new Error("NOT_IMPLEMENTED");
}

// Menghapus sesi (logout atau respons 401).
export function clearSession(): void {
  throw new Error("NOT_IMPLEMENTED");
}
