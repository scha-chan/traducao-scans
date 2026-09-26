FROM node:22-alpine AS builder

ARG API_BASE_URL=http://localhost:8000
ENV API_BASE_URL=$API_BASE_URL

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# ─── Servidor de produção ────────────────────────────────────────────────────
FROM nginx:alpine
COPY --from=builder /app/dist/frontend/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
