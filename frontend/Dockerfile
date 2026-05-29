# ── Stage 1: Build the Vite/React app ────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json .
RUN npm ci --frozen-lockfile
COPY . .
RUN npm run build

# ── Stage 2: Serve via nginx ─────────────────────────────────────
FROM nginx:1.27-alpine AS runtime
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget -qO- http://localhost:80/health || exit 1

EXPOSE 80
