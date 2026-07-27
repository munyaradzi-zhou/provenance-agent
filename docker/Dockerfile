# Multi-stage build: fat builder compiles/installs deps, slim runtime ships only
# what's needed. Smaller image = faster ECS pulls, smaller attack surface.

# ---- builder ---------------------------------------------------------------
FROM python:3.11.9-slim-bookworm AS builder
WORKDIR /app
# Install runtime deps into an isolated prefix we copy into the runtime stage.
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- runtime ---------------------------------------------------------------
FROM python:3.11.9-slim-bookworm AS runtime

# Run as a non-root user (defense in depth: a container escape isn't root).
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app

# Bring in the installed packages from the builder, then the app code.
COPY --from=builder /install /usr/local
COPY app ./app

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER appuser
EXPOSE 8000

# Container-level healthcheck hits the liveness endpoint.
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=2).status==200 else 1)"

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
