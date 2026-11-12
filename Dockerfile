# syntax=docker/dockerfile:1

# ---- builder: install runtime deps into a venv with uv --------------------- #
# python:3.12 (trixie-slim) with uv pre-installed, pinned to the uv version
# that produced uv.lock. Using the official Python keeps the venv's interpreter
# path identical to the final stage below.
FROM ghcr.io/astral-sh/uv:0.12.17-python3.12-trixie-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /build

# Install only runtime dependencies (no dev group) into /opt/venv. Copy the
# manifests first so this layer is cached until pyproject.toml/uv.lock change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# ---- final: venv + app code only, running as a non-root user --------------- #
FROM python:3.12-slim

RUN useradd --create-home --uid 10001 app

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY --from=builder --chown=app:app /opt/venv /opt/venv
COPY --chown=app:app app ./app

USER app

EXPOSE 8080

# No curl in the image; use python's stdlib to hit /health.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request,os; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8080')+'/health', timeout=3)"]

# shell form so $PORT expands; exec keeps uvicorn as PID 1.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
