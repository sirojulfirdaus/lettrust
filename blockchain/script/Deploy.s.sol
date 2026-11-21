// SPDX-License-Identifier: MIT
// Owner: Sat (PIC 6) | Status: COMPLETE | Ref: SA §6.7
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {OfferProofRegistry} from "../src/OfferProofRegistry.sol";

/// Script deployment OfferProofRegistry ke chain lokal menggunakan signer registrar.
contract Deploy is Script {
    /// Men-deploy registry; akun dari REGISTRY_SIGNER_PRIVATE_KEY menjadi registrar.
    function run() external returns (OfferProofRegistry registry) {
        uint256 signerKey = vm.envUint("REGISTRY_SIGNER_PRIVATE_KEY");
        vm.startBroadcast(signerKey);
        registry = new OfferProofRegistry();
        vm.stopBroadcast();
        console.log("OfferProofRegistry deployed at", address(registry));
    }
}
