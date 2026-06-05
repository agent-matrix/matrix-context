# syntax=docker/dockerfile:1
# Matrix Context Console — Hugging Face Docker Space.
# Single source of truth is ../frontend (native app + launcher) and ../src
# (backend). Build context is the repo root:
#   docker build -f hf/Dockerfile -t matrix-context-console .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOST=0.0.0.0 \
    PORT=7860 \
    MATRIX_CONTEXT_PATH=:memory:

WORKDIR /app

# 1) Backend — cached unless the package sources change.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install .

# 2) Frontend — the native app is the single source of truth (not duplicated).
COPY frontend ./frontend

# 3) Run as a non-root user (Hugging Face runs containers as uid 1000).
RUN useradd -m -u 1000 user && chown -R user /app
USER user

EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=4s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ['PORT']+'/v1/health', timeout=3)" || exit 1

CMD ["python", "frontend/server.py"]
