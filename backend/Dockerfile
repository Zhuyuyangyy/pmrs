# =============================================================================
# PMRS Backend Dockerfile - Multi-stage build
# =============================================================================

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Production
FROM python:3.11-slim AS production

# Add metadata
LABEL maintainer="PMRS Team"
LABEL version="1.0.0"
LABEL description="PMRS - Industrial Control Protocol Vulnerability Mining System"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    afl++ \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r pmrs && useradd -r -g pmrs -d /app -s /sbin/nologin pmrs

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Create directories with proper permissions
RUN mkdir -p /tmp/afl_input /tmp/afl_output /app/logs && \
    chown -R pmrs:pmrs /app /tmp/afl_input /tmp/afl_output

# Switch to non-root user
USER pmrs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Run with Gunicorn in production
CMD ["gunicorn", "main:app", "-c", "gunicorn_conf.py"]
