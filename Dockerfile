# Stage 1: Build Next.js static export
FROM node:20-alpine AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
ENV NEXT_PUBLIC_API_URL=/api/v1
RUN npm run build

# Stage 2: Python runtime with static UI + API
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ /app/backend/
COPY --from=frontend-build /build/frontend/out /app/static

ENV PYTHONPATH=/app/backend
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite+aiosqlite:////data/security_dashboard.db
ENV STATIC_DIR=/app/static
ENV REPORTS_OUTPUT_DIR=/data/reports
ENV CHARTS_OUTPUT_DIR=/data/charts
ENV CORS_ORIGINS=*

RUN mkdir -p /data /data/reports /data/charts

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080
VOLUME ["/data"]

ENTRYPOINT ["/entrypoint.sh"]
