// Owner: Van (PIC 2) | Status: COMPLETE | Ref: PRD FR-01.02, §9.11; SA §10.5 (S-03), §11.2.2
import { describe, expect, it } from "vitest";
import { buildProfileFetchKey, shouldFetchProfile } from "./profile-fetch";

describe("keputusan pemuatan profil S-03 di header", () => {
  it("menyusun kunci dari token, path, dan revisi; null tanpa sesi", () => {
    expect(buildProfileFetchKey("tok", "/hr", 0)).toBe("tok|/hr|0");
    expect(buildProfileFetchKey("tok", "/hr/proofs", 0)).not.toBe(buildProfileFetchKey("tok", "/hr", 0));
    expect(buildProfileFetchKey("tok", "/hr", 1)).not.toBe(buildProfileFetchKey("tok", "/hr", 0));
    expect(buildProfileFetchKey(null, "/hr", 0)).toBeNull();
  });

  it("tidak memuat tanpa sesi", () => {
    expect(shouldFetchProfile(null, null, false)).toBe(false);
  });

  it("memuat ulang saat navigasi, revisi sesi, atau token berubah", () => {
    const last = { key: "tok|/hr|0", status: "loaded" } as const;
    expect(shouldFetchProfile("tok|/hr|0", null, false)).toBe(true);
    expect(shouldFetchProfile("tok|/hr/proofs|0", last, true)).toBe(true);
    expect(shouldFetchProfile("tok|/hr|1", last, true)).toBe(true);
    expect(shouldFetchProfile("tok2|/hr|0", last, true)).toBe(true);
  });

  it("tidak menggandakan permintaan untuk kunci yang sama", () => {
    expect(shouldFetchProfile("tok|/hr|0", { key: "tok|/hr|0", status: "loading" }, false)).toBe(false);
    expect(shouldFetchProfile("tok|/hr|0", { key: "tok|/hr|0", status: "loaded" }, true)).toBe(false);
  });

  it("memuat ulang kunci yang sama bila permintaan sebelumnya gagal atau profil hilang", () => {
    expect(shouldFetchProfile("tok|/hr|0", { key: "tok|/hr|0", status: "failed" }, true)).toBe(true);
    expect(shouldFetchProfile("tok|/hr|0", { key: "tok|/hr|0", status: "loaded" }, false)).toBe(true);
  });
});
