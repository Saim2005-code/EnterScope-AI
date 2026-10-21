# syntax=docker/dockerfile:1
# ==========================================
# Stage 1: Builder
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Configure pip globally for resilient downloads inside WSL2 Docker bridge
ENV PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Use BuildKit cache mount so downloaded wheels persist even if a network dip occurs
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install --prefix=/install --timeout=120 --retries=10 -r requirements.txt

# ==========================================
# Stage 2: Production Runtime
# ==========================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy pre-built Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ ./app/

# Create directory for ONNX model cache inside container
RUN mkdir -p /app/.fastembed_cache

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
