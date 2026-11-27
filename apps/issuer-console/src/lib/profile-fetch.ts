// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.02, §9.11; SA §10.5 (S-03), §11.2.2

// Jejak permintaan S-03 terakhir di header; "failed" juga dipakai untuk permintaan yang dibatalkan sebelum selesai.
export type ProfileFetchRecord = {
  key: string;
  status: "loading" | "loaded" | "failed";
};

// Menyusun kunci dedupe S-03 dari token, path, dan revisi sesi; null bila tidak ada sesi.
export function buildProfileFetchKey(
  accessToken: string | null,
  pathname: string,
  revision: number,
): string | null {
  return accessToken ? `${accessToken}|${pathname}|${revision}` : null;
}

// Menentukan perlu tidaknya memanggil S-03: kunci baru, atau kunci sama yang gagal/tanpa profil; tidak menggandakan permintaan yang masih berjalan.
export function shouldFetchProfile(
  key: string | null,
  last: ProfileFetchRecord | null,
  hasProfile: boolean,
): boolean {
  if (key === null) {
    return false;
  }
  if (last === null || last.key !== key) {
    return true;
  }
  if (last.status === "loading") {
    return false;
  }
  return last.status === "failed" || !hasProfile;
}
