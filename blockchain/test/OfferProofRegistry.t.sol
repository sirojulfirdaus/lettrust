// SPDX-License-Identifier: MIT
// Owner: Sat (PIC 6) | Status: STUB | Ref: PRD FR-03.03, FR-04.02–FR-04.04; SA §6.2.3
// TODO: Tambahkan 10 test wajib SA §6.2.3 (daftar di bawah) setelah fungsi contract diimplementasikan.
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {OfferProofRegistry} from "../src/OfferProofRegistry.sol";

// Test wajib SA §6.2.3 yang harus ditulis pemilik modul:
// 1. Issue berhasil: data tersimpan, status Active, event ProofIssued.
// 2. Issue duplikat: revert ProofAlreadyExists; data awal tidak berubah.
// 3. Issue input nol: revert InvalidInput.
// 4. Issue oleh non-registrar: revert NotRegistrar.
// 5. Revoke berhasil: status Revoked, revokedAt > 0, hash dan issuedAt tetap, event ProofRevoked.
// 6. Revoke dua kali: revert ProofNotActive.
// 7. Revoke issuerRef berbeda: revert IssuerMismatch (SCN-14e).
// 8. Revoke bukti tidak ada: revert ProofNotFound.
// 9. Revoke oleh non-registrar: revert NotRegistrar.
// 10. getProof tidak ada: exists=false.

/// Unit test OfferProofRegistry.
contract OfferProofRegistryTest is Test {
    OfferProofRegistry internal registry;

    /// Men-deploy registry dengan kontrak test sebagai deployer.
    function setUp() public {
        registry = new OfferProofRegistry();
    }

    /// Memastikan registrar sama dengan akun yang men-deploy contract.
    function test_RegistrarIsDeployer() public view {
        assertEq(registry.registrar(), address(this));
    }
}
