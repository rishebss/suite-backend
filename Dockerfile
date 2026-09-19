# suite-backend — Django 6 + DRF + Channels (ASGI) deployment image
# Serves HTTP *and* WebSocket (daphne) on a single port ($PORT).
# Platform contract: build the image, run it, provide env vars, expose $PORT.

# ---------------------------------------------------------------------------
# builder: compile wheels into an isolated prefix
# ---------------------------------------------------------------------------
FROM python:3.14-slim AS builder

# libcairo2-dev / libpq-dev match the existing railpack.json build requirement
# and let psycopg/reportlab/lxml compile if no wheel is available.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential libcairo2-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------------------------------------------------------------------------
# runtime: slim image with only the shared libraries the app needs
# ---------------------------------------------------------------------------
FROM python:3.14-slim

# libcairo2 for PDF generation; psycopg[binary] ships its own libpq.
# curl is for the container healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libcairo2 curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=core.settings \
    PORT=8000

WORKDIR /app

# Wheels from the builder stage (same base image => same interpreter path).
COPY --from=builder /install /usr/local

# Application code.
COPY . .

RUN chmod +x entrypoint.sh \
    && useradd -m django \
    && chown -R django:django /app

USER django

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/" || exit 1

ENTRYPOINT ["./entrypoint.sh"]
