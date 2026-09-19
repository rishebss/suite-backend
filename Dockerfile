FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=core.settings

WORKDIR /app

# System deps: libpq for psycopg, libjpeg/zlib for Pillow, libcairo2 for PDF gen.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (cached layer)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY . .

# Collect static files. Allow failure if DB/static isn't resolvable at build time.
RUN python manage.py collectstatic --noinput || echo "collectstatic skipped"

EXPOSE 8000

# Run migrations then start gunicorn (WSGI).
# Uses $PORT if the platform provides it (Koyeb/Render/Railway), else 8000.
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn core.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 120 --access-logfile - --error-logfile -"]
