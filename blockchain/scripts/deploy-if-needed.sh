#!/usr/bin/env bash
# Owner: Sat (PIC 6) | Status: COMPLETE | Ref: SA §6.7
# Men-deploy OfferProofRegistry hanya bila info deployment belum ada atau alamatnya tidak memiliki kode.
set -euo pipefail

RPC_URL="${REGISTRY_RPC_URL:?REGISTRY_RPC_URL wajib diisi}"
: "${REGISTRY_SIGNER_PRIVATE_KEY:?REGISTRY_SIGNER_PRIVATE_KEY wajib diisi}"
DEPLOYMENT_FILE="${DEPLOYMENT_FILE:-/shared/deployments/local.json}"
CONTRACT="OfferProofRegistry"

# Mengambil nilai string field JSON sederhana (tanpa jq) dari berkas.
json_field() {
    sed -n "s/.*\"$2\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" "$1" | head -n 1
}

mkdir -p "$(dirname "$DEPLOYMENT_FILE")"

if [[ -f "$DEPLOYMENT_FILE" ]]; then
    existing="$(json_field "$DEPLOYMENT_FILE" contractAddress)"
    if [[ "$existing" =~ ^0x[0-9a-fA-F]{40}$ ]]; then
        code="$(cast code "$existing" --rpc-url "$RPC_URL")"
        if [[ "$code" != "0x" && -n "$code" ]]; then
            echo "[deployer] Contract sudah ada di $existing; deployment dilewati."
            exit 0
        fi
        echo "[deployer] Alamat $existing tidak memiliki kode (state chain baru); deploy ulang."
    else
        echo "[deployer] Berkas deployment tidak valid; deploy ulang."
    fi
fi

echo "[deployer] Men-deploy $CONTRACT ke $RPC_URL ..."
forge script script/Deploy.s.sol:Deploy --rpc-url "$RPC_URL" --broadcast --slow

chain_id="$(cast chain-id --rpc-url "$RPC_URL")"
run_file="broadcast/Deploy.s.sol/${chain_id}/run-latest.json"
[[ -f "$run_file" ]] || { echo "[deployer] Berkas broadcast $run_file tidak ditemukan." >&2; exit 1; }

address="$(grep -o '"contractAddress": *"0x[0-9a-fA-F]\{40\}"' "$run_file" | head -n 1 | grep -o '0x[0-9a-fA-F]\{40\}')"
tx_hash="$(grep -o '"transactionHash": *"0x[0-9a-fA-F]\{64\}"' "$run_file" | head -n 1 | grep -o '0x[0-9a-fA-F]\{64\}')"
[[ -n "$address" && -n "$tx_hash" ]] || { echo "[deployer] Alamat/tx deployment tidak terbaca." >&2; exit 1; }

code="$(cast code "$address" --rpc-url "$RPC_URL")"
[[ "$code" != "0x" ]] || { echo "[deployer] Kode contract tidak ditemukan di $address." >&2; exit 1; }

block="$(cast receipt "$tx_hash" blockNumber --rpc-url "$RPC_URL")"
deployer="$(cast wallet address --private-key "$REGISTRY_SIGNER_PRIVATE_KEY")"
abi_sha256="$(forge inspect "$CONTRACT" abi --json | sha256sum | cut -d ' ' -f 1)"

tmp_file="${DEPLOYMENT_FILE}.tmp"
cat > "$tmp_file" <<EOF
{
  "chainId": ${chain_id},
  "contractAddress": "${address}",
  "deployer": "${deployer}",
  "deployedAtBlock": ${block},
  "abiSha256": "${abi_sha256}"
}
EOF
mv "$tmp_file" "$DEPLOYMENT_FILE"
echo "[deployer] Deployment tersimpan di $DEPLOYMENT_FILE (contract $address, blok $block)."
