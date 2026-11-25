// SPDX-License-Identifier: MIT
// Owner: Sat (PIC 6) | Status: COMPLETE | Ref: PRD FR-03.03, FR-04.02–FR-04.04; SA §6.2.3
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {OfferProofRegistry} from "../src/OfferProofRegistry.sol";

/// Menguji lifecycle bukti, otorisasi registrar, dan seluruh kasus wajib SA §6.2.3.
contract OfferProofRegistryTest is Test {
    bytes32 private constant PROOF_ID = keccak256("lettrust:synthetic:proof:1");
    address private constant NON_REGISTRAR = address(0xBEEF);
    uint64 private constant ISSUED_AT = 1_790_000_000;
    uint64 private constant REVOKED_AT = ISSUED_AT + 3600;

    // Hash dihitung saat konstruksi test agar precompile SHA-256 tidak menghabiskan expectRevert atau prank.
    bytes32 private immutable DOCUMENT_HASH = sha256("Offer letter sintetis untuk pengujian registry.");
    bytes32 private immutable ISSUER_REF = sha256("lettrust:issuer:ISS-7K3M9Q2H");
    bytes32 private immutable OTHER_DOCUMENT_HASH = sha256("Berkas sintetis pengganti.");
    bytes32 private immutable OTHER_ISSUER_REF = sha256("lettrust:issuer:ISS-4D8N2P6R");

    OfferProofRegistry internal registry;

    /// Men-deploy registry dengan kontrak test sebagai registrar dan waktu awal yang tetap.
    function setUp() public {
        registry = new OfferProofRegistry();
        vm.warp(ISSUED_AT);
    }

    /// Memastikan registrar sama dengan akun yang men-deploy contract.
    function test_RegistrarIsDeployer() public view {
        assertEq(registry.registrar(), address(this));
    }

    /// Memastikan penerbitan menyimpan seluruh data Active dan memancarkan event dari registry.
    function test_IssueStoresActiveProofAndEmitsEvent() public {
        vm.expectEmit(true, true, false, true, address(registry));
        emit OfferProofRegistry.ProofIssued(PROOF_ID, ISSUER_REF, DOCUMENT_HASH, ISSUED_AT);

        registry.issueProof(PROOF_ID, DOCUMENT_HASH, ISSUER_REF);

        _assertActiveProof();
    }

    /// Menolak proofId duplikat tanpa menimpa hash, penerbit, status, atau waktu awal.
    function test_IssueDuplicateRevertsWithoutChangingProof() public {
        registry.issueProof(PROOF_ID, DOCUMENT_HASH, ISSUER_REF);
        vm.warp(REVOKED_AT);

        vm.expectRevert(OfferProofRegistry.ProofAlreadyExists.selector);
        registry.issueProof(PROOF_ID, OTHER_DOCUMENT_HASH, OTHER_ISSUER_REF);

        _assertActiveProof();
    }

    /// Menolak ketujuh kombinasi input nol tanpa membuat bukti baru.
    function test_IssueZeroInputsRevert() public {
        for (uint8 mask = 1; mask < 8; mask++) {
            bytes32 proofId = (mask & 1) != 0 ? bytes32(0) : PROOF_ID;
            bytes32 documentHash = (mask & 2) != 0 ? bytes32(0) : DOCUMENT_HASH;
            bytes32 issuerRef = (mask & 4) != 0 ? bytes32(0) : ISSUER_REF;

            vm.expectRevert(OfferProofRegistry.InvalidInput.selector);
            registry.issueProof(proofId, documentHash, issuerRef);
        }

        _assertMissingProof(PROOF_ID);
        _assertMissingProof(bytes32(0));
    }

    /// Menolak penerbitan oleh selain registrar tanpa membuat bukti.
    function test_IssueByNonRegistrarReverts() public {
        vm.expectRevert(OfferProofRegistry.NotRegistrar.selector);
        vm.prank(NON_REGISTRAR);
        registry.issueProof(PROOF_ID, DOCUMENT_HASH, ISSUER_REF);

        _assertMissingProof(PROOF_ID);
    }

    /// Memastikan pencabutan menyimpan waktu dan event baru sambil mempertahankan data penerbitan.
    function test_RevokePreservesIssuanceDataAndEmitsEvent() public {
        registry.issueProof(PROOF_ID, DOCUMENT_HASH, ISSUER_REF);
        vm.warp(REVOKED_AT);

        vm.expectEmit(true, true, false, true, address(registry));
        emit OfferProofRegistry.ProofRevoked(PROOF_ID, ISSUER_REF, REVOKED_AT);

        registry.revokeProof(PROOF_ID, ISSUER_REF);

        _assertRevokedProof();
    }

    /// Menolak pencabutan ulang dan mempertahankan waktu pencabutan pertama.
    function test_RevokeTwiceRevertsWithoutChangingProof() public {
        registry.issueProof(PROOF_ID, DOCUMENT_HASH, ISSUER_REF);
        vm.warp(REVOKED_AT);
        registry.revokeProof(PROOF_ID, ISSUER_REF);
        vm.warp(REVOKED_AT + 3600);

        vm.expectRevert(OfferProofRegistry.ProofNotActive.selector);
        registry.revokeProof(PROOF_ID, ISSUER_REF);

        _assertRevokedProof();
    }

    /// Menolak pencabutan lintas penerbit meskipun pemanggil adalah registrar.
    function test_RevokeWithDifferentIssuerReverts() public {
        registry.issueProof(PROOF_ID, DOCUMENT_HASH, ISSUER_REF);
        vm.warp(REVOKED_AT);

        vm.expectRevert(OfferProofRegistry.IssuerMismatch.selector);
        registry.revokeProof(PROOF_ID, OTHER_ISSUER_REF);

        _assertActiveProof();
    }

    /// Menolak pencabutan bukti yang belum pernah diterbitkan.
    function test_RevokeMissingProofReverts() public {
        vm.expectRevert(OfferProofRegistry.ProofNotFound.selector);
        registry.revokeProof(PROOF_ID, ISSUER_REF);

        _assertMissingProof(PROOF_ID);
    }

    /// Menolak pencabutan oleh selain registrar dan mempertahankan status Active.
    function test_RevokeByNonRegistrarReverts() public {
        registry.issueProof(PROOF_ID, DOCUMENT_HASH, ISSUER_REF);
        vm.warp(REVOKED_AT);

        vm.expectRevert(OfferProofRegistry.NotRegistrar.selector);
        vm.prank(NON_REGISTRAR);
        registry.revokeProof(PROOF_ID, ISSUER_REF);

        _assertActiveProof();
    }

    /// Memastikan pembaca publik menerima exists=false dan seluruh nilai nol untuk bukti yang tidak ada.
    function test_GetMissingProofReturnsZeroValues() public {
        vm.startPrank(NON_REGISTRAR);
        _assertMissingProof(PROOF_ID);
        _assertMissingProof(bytes32(0));
        vm.stopPrank();
    }

    /// Menolak penerbitan ulang proofId yang sudah dicabut agar status Revoked tetap final.
    function test_IssueRevokedProofRevertsWithoutReactivation() public {
        registry.issueProof(PROOF_ID, DOCUMENT_HASH, ISSUER_REF);
        vm.warp(REVOKED_AT);
        registry.revokeProof(PROOF_ID, ISSUER_REF);
        vm.warp(REVOKED_AT + 3600);

        vm.expectRevert(OfferProofRegistry.ProofAlreadyExists.selector);
        registry.issueProof(PROOF_ID, OTHER_DOCUMENT_HASH, ISSUER_REF);

        _assertRevokedProof();
    }

    /// Memeriksa seluruh field bukti Active terhadap data sintetis yang diterbitkan.
    function _assertActiveProof() internal view {
        _assertProof(
            PROOF_ID,
            OfferProofRegistry.Proof({
                documentHash: DOCUMENT_HASH,
                issuerRef: ISSUER_REF,
                status: OfferProofRegistry.Status.Active,
                issuedAt: ISSUED_AT,
                revokedAt: 0
            })
        );
    }

    /// Memeriksa seluruh field bukti Revoked termasuk waktu pencabutan pertama.
    function _assertRevokedProof() internal view {
        _assertProof(
            PROOF_ID,
            OfferProofRegistry.Proof({
                documentHash: DOCUMENT_HASH,
                issuerRef: ISSUER_REF,
                status: OfferProofRegistry.Status.Revoked,
                issuedAt: ISSUED_AT,
                revokedAt: REVOKED_AT
            })
        );
    }

    /// Memeriksa bahwa bukti yang tidak ada mengembalikan seluruh field bernilai nol.
    function _assertMissingProof(bytes32 proofId) internal view {
        OfferProofRegistry.Proof memory emptyProof;
        _assertProof(proofId, emptyProof);
    }

    /// Membandingkan seluruh hasil getProof, termasuk exists, dengan data yang diharapkan.
    function _assertProof(bytes32 proofId, OfferProofRegistry.Proof memory expected) internal view {
        (bool exists, bytes32 documentHash, bytes32 issuerRef, uint8 status, uint64 issuedAt, uint64 revokedAt) =
            registry.getProof(proofId);

        assertEq(exists, expected.status != OfferProofRegistry.Status.None, "exists");
        assertEq(documentHash, expected.documentHash, "documentHash");
        assertEq(issuerRef, expected.issuerRef, "issuerRef");
        assertEq(status, uint8(expected.status), "status");
        assertEq(issuedAt, expected.issuedAt, "issuedAt");
        assertEq(revokedAt, expected.revokedAt, "revokedAt");
    }
}
