# syntax=docker/dockerfile:1.7
# API service: FastAPI + WebSockets. Frontend lives in web/ as a separate image.

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH

COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev

# Model checkpoints + seed elo baked into the image (filtered by .dockerignore).
COPY artifacts ./artifacts
# Telemetry DB lives on a separate path so a mounted volume doesn't shadow
# the baked-in checkpoints / elo seed.
RUN mkdir -p /data
ENV OWARE_DB=/data/telemetry.db \
    OWARE_ELO=/app/artifacts/elo.json \
    OWARE_HOST=0.0.0.0

EXPOSE 8000
CMD ["uv", "run", "python", "-m", "oware.server"]
