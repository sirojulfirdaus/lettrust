# Owner: Van (PIC 2) | Status: COMPLETE | Ref: SA §11.2, §12.2, §15.1
# Image Lettrust Console: build Next.js standalone lalu jalankan sebagai user non-root.
FROM node:24.22.3-trixie-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:24.22.3-trixie-slim AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
# Base URL backend disisipkan ke bundle browser saat build (bukan secret).
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:24.22.3-trixie-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
