# syntax=docker/dockerfile:1.7

FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_DEFAULT_TIMEOUT=120

WORKDIR /build

RUN python -m venv /opt/venv

COPY requirements.txt .
COPY vendor/wheels/ ./wheels/

RUN /opt/venv/bin/pip install --no-index --find-links=/build/wheels -r requirements.txt


FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"
ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000
ENV AUTH_TOKEN=
ENV SERVICE_NAME=iot-ingestion
ENV SERVICE_VERSION=0.5.0
ENV AI_SERVICE_URL=http://ai-service:9000
ENV POSTGRES_HOST=db
ENV POSTGRES_PORT=5432

WORKDIR /app

RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup --home /app appuser

COPY --from=builder /opt/venv /opt/venv
COPY src/ ./src/

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()" || exit 1

CMD ["sh", "-c", "uvicorn iot_app.main:app --app-dir src --host ${APP_HOST} --port ${APP_PORT}"]
