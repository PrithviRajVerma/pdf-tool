# ==============================================================================
# Multi-stage Dockerfile for pdf-tool
# Stage 1: Build wheel using astral-sh/uv
# Stage 2: Production runtime with LibreOffice, Tesseract, Ghostscript, Poppler
# ==============================================================================

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /build

# Copy project definition and source code
COPY pyproject.toml uv.lock README.md /build/
COPY pdf_tool/ /build/pdf_tool/

# Build wheel distribution
RUN uv build --wheel --out-dir /build/dist


# ==============================================================================
# Runtime Stage
# ==============================================================================
FROM python:3.12-slim-bookworm AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install required system tools and document engines
RUN apt-get update && apt-get install -y --no-install-recommends \
    ghostscript \
    libreoffice-nogui \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libmagic1 \
    fonts-dejavu-core \
    fonts-liberation \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install the built wheel
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -rf /tmp/*.whl

# Setup working directory for document mounts
WORKDIR /data
VOLUME ["/data"]

# Default non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /data
USER appuser

ENTRYPOINT ["pdf"]
CMD ["--help"]
