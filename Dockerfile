# ==========================================
# Stage 1: Builder
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

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
