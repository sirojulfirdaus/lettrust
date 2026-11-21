// SPDX-License-Identifier: MIT
// Owner: Sat (PIC 6) | Status: STUB | Ref: PRD FR-03.03, FR-04.02, FR-04.04; SA §6.2
// TODO: Implementasikan issueProof, revokeProof, dan getProof sesuai aturan SA §6.2.2, lalu hapus error NotImplemented.
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
    /// Sementara selama scaffolding: fungsi yang belum diimplementasikan selalu revert.
    error NotImplemented();

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
        proofId;
        documentHash;
        issuerRef;
        revert NotImplemented();
    }

    /// Mencabut bukti Active milik issuerRef yang sama; data lain tidak diubah dan tidak ada reaktivasi.
    function revokeProof(bytes32 proofId, bytes32 issuerRef) external onlyRegistrar {
        proofId;
        issuerRef;
        revert NotImplemented();
    }

    /// Membaca bukti; mengembalikan exists=false dan nilai nol bila tidak ada (versi final tidak pernah revert).
    function getProof(bytes32 proofId)
        external
        view
        returns (bool exists, bytes32 documentHash, bytes32 issuerRef, uint8 status, uint64 issuedAt, uint64 revokedAt)
    {
        proofId;
        exists;
        documentHash;
        issuerRef;
        status;
        issuedAt;
        revokedAt;
        revert NotImplemented();
    }
}
