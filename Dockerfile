FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system ari \
    && adduser --system --ingroup ari ari

RUN apt-get update \
    && apt-get install -y --no-install-recommends libjpeg62-turbo-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/backend/requirements.txt

COPY backend /app/backend
WORKDIR /app/backend

RUN DJANGO_DEBUG=1 python manage.py collectstatic --noinput
RUN chmod +x /app/backend/start.sh \
    && chown -R ari:ari /app

EXPOSE 8000

USER ari

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/', timeout=3)" || exit 1

ENTRYPOINT ["/app/backend/start.sh"]
