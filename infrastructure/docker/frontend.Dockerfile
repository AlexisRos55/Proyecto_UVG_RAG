# Multi-stage build: compila el SPA con Vite, lo sirve como archivos estaticos con nginx.
FROM node:22-slim AS builder

WORKDIR /build

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

FROM nginx:1.27-alpine AS final

COPY --from=builder /build/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 5173

# 127.0.0.1, no "localhost": /etc/hosts en esta imagen resuelve localhost a ::1 primero, y
# nginx solo escucha IPv4 (ver nginx.conf) -- con "localhost" el healthcheck fallaba con
# "connection refused" pese a que el sitio respondia bien por fuera del contenedor.
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD wget -q -O /dev/null http://127.0.0.1:5173/ || exit 1
