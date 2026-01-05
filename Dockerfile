# Multi-stage Dockerfile for VortexDB
# Optimized for smaller image size and security

# ===========================================
# Stage 1: Builder
# ===========================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.lock.txt requirements.txt ./
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.lock.txt

# ===========================================
# Stage 2: Production
# ===========================================
FROM python:3.11-slim AS production

# Set environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src:/app \
    VECTORDB_ENV=production \
    APP_MODE=production

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with home directory
RUN groupadd -r vortex && useradd -r -g vortex -d /home/vortex -m vortex
ENV HF_HOME=/app/data/model_cache

# Copy wheels from builder and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index /wheels/* \
    && rm -rf /wheels

# Copy source code
COPY --chown=vortex:vortex . .

# Pre-download models to bake them into the image
# This increases image size but allows faster startup/offline usage
RUN python3 scripts/download_models.py

# Create required directories
RUN mkdir -p logs && chown -R vortex:vortex /app

# Switch to non-root user
USER vortex

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose API port
EXPOSE 8000

# Default command
CMD ["uvicorn", "llm_backend.server.vector_server.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ===========================================
# Stage 3: Development
# ===========================================
FROM production AS development

USER root

# Install development dependencies
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

USER vortex

# Enable debug mode
ENV VECTORDB_DEBUG=1

CMD ["uvicorn", "llm_backend.server.vector_server.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
