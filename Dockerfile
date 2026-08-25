#---------------------------------------------------------------------------
# RideWise — Multi-stage build for FastAPI scoring service
#---------------------------------------------------------------------------
# Stage 1: Builder — compile dependencies into wheels (cached)
#---------------------------------------------------------------------------

FROM python:3.11.9-slim as builder

# Build-time dependencies for wheel compilation (numpy, scipy, scikit-learn)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies into wheels (isolation + caching)
COPY requirements.txt .
RUN pip install --upgrade pip setuptools && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

#---------------------------------------------------------------------------
# Stage 2: Runtime — minimal image, pre-built wheels only
#---------------------------------------------------------------------------

FROM python:3.11.9-slim

LABEL maintainer="ridewise-team" \
      description="RideWise churn prediction API & analytics dashboard" \
      version="1.0.0"

# Stream logs directly to console for `docker logs` and journald visibility
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Runtime-only system libraries (libgomp1 for scikit-learn, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy pre-built wheels from builder stage (no compilation in final image)
COPY --from=builder /app/wheels /app/wheels
COPY requirements.txt .
RUN pip install --no-cache /app/wheels/* && rm -rf /app/wheels

# Copy application code and model artifacts
COPY src/ ./src/
COPY models/ ./models/

# Create non-root user for security (never run as root)
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Healthcheck using curl (fast, built-in)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

# Start FastAPI service (bind to 0.0.0.0 in container, published to 127.0.0.1 on host)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
