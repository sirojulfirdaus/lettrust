# Owner: Pash (PIC 4) | Status: COMPLETE | Ref: SA §11.3, §12.2, §15.1
# Image Portal Karier Mitra (Simulasi): build Next.js standalone lalu jalankan sebagai user non-root.
# LETTRUST_API_BASE_URL, LETTRUST_PARTNER_TOKEN, PORTAL_UPSTREAM_TIMEOUT_MS diberikan Compose saat runtime, tidak dibakar ke image.
FROM node:24.22.3-trixie-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:24.22.3-trixie-slim AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:24.22.3-trixie-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3001
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
USER node
EXPOSE 3001
CMD ["node", "server.js"]
