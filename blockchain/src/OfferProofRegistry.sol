// SPDX-License-Identifier: MIT
// Owner: Sat (PIC 6) | Status: COMPLETE | Ref: PRD FR-03.03, FR-04.02, FR-04.04; SA §6.2
pragma solidity ^0.8.24;

/// Registry bukti penerbitan offer letter Lettrust (prototipe D3).
contract OfferProofRegistry {
    enum Status {
        None,
        Active,
        Revoked
    }

    struct Proof {
        bytes32 documentHash; // SHA-256 byte berkas final
        bytes32 issuerRef; // referensi penerbit opaque
        Status status;
        uint64 issuedAt; // block.timestamp
        uint64 revokedAt; // 0 jika belum dicabut
    }

    address public immutable registrar;
    mapping(bytes32 => Proof) private proofs;

    event ProofIssued(bytes32 indexed proofId, bytes32 indexed issuerRef, bytes32 documentHash, uint64 issuedAt);
    event ProofRevoked(bytes32 indexed proofId, bytes32 indexed issuerRef, uint64 revokedAt);

    error NotRegistrar();
    error InvalidInput();
    error ProofAlreadyExists();
    error ProofNotFound();
    error ProofNotActive();
    error IssuerMismatch();

    /// Menetapkan deployer sebagai registrar tunggal yang tidak dapat diubah.
    constructor() {
        registrar = msg.sender;
    }

    /// Membatasi fungsi tulis hanya untuk signer registrar backend.
    modifier onlyRegistrar() {
        if (msg.sender != registrar) revert NotRegistrar();
        _;
    }

    /// Mencatat bukti penerbitan baru berstatus Active; menolak input nol dan proofId yang sudah ada.
    function issueProof(bytes32 proofId, bytes32 documentHash, bytes32 issuerRef) external onlyRegistrar {
        if (proofId == bytes32(0) || documentHash == bytes32(0) || issuerRef == bytes32(0)) revert InvalidInput();
        if (proofs[proofId].status != Status.None) revert ProofAlreadyExists();

        uint64 issuedAt = uint64(block.timestamp);
        proofs[proofId] = Proof({
            documentHash: documentHash, issuerRef: issuerRef, status: Status.Active, issuedAt: issuedAt, revokedAt: 0
        });

        emit ProofIssued(proofId, issuerRef, documentHash, issuedAt);
    }

    /// Mencabut bukti Active milik issuerRef yang sama; data lain tidak diubah dan tidak ada reaktivasi.
    function revokeProof(bytes32 proofId, bytes32 issuerRef) external onlyRegistrar {
        Proof storage proof = proofs[proofId];
        if (proof.status == Status.None) revert ProofNotFound();
        if (proof.status != Status.Active) revert ProofNotActive();
        if (proof.issuerRef != issuerRef) revert IssuerMismatch();

        uint64 revokedAt = uint64(block.timestamp);
        proof.status = Status.Revoked;
        proof.revokedAt = revokedAt;

        emit ProofRevoked(proofId, issuerRef, revokedAt);
    }

    /// Membaca bukti tanpa otorisasi; mengembalikan exists=false dan nilai nol bila tidak ada.
    function getProof(bytes32 proofId)
        external
        view
        returns (bool exists, bytes32 documentHash, bytes32 issuerRef, uint8 status, uint64 issuedAt, uint64 revokedAt)
    {
        Proof storage proof = proofs[proofId];
        return (
            proof.status != Status.None,
            proof.documentHash,
            proof.issuerRef,
            uint8(proof.status),
            proof.issuedAt,
            proof.revokedAt
        );
    }
}
