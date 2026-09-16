FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system nkata \
    && adduser --system --ingroup nkata nkata

WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY . ./
COPY --from=frontend /app/frontend/dist ./frontend/dist
RUN chmod +x scripts/start-production.sh \
    && mkdir -p media private_media staticfiles \
    && chown -R nkata:nkata /app

USER nkata
EXPOSE 8000
CMD ["./scripts/start-production.sh"]
