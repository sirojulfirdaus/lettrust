# Owner: Sat (PIC 6) | Status: COMPLETE | Ref: SA §6.7, §15.1
# Image one-shot chain-deployer: build contract saat build image, deploy saat dijalankan (bila perlu).
FROM ghcr.io/foundry-rs/foundry:v1.9.0

USER root
RUN mkdir -p /app /shared/deployments && chown -R foundry:foundry /app /shared
WORKDIR /app
COPY --chown=foundry:foundry . /app
USER foundry

RUN forge build && forge inspect OfferProofRegistry abi --json > /dev/null

ENTRYPOINT []
CMD ["bash", "scripts/deploy-if-needed.sh"]
