# ==========================================
# Stage 1: Builder
# ==========================================
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install build dependencies if necessary
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy configuration and source code
COPY pyproject.toml README.md ./
COPY src/ src/

# Install the application and its dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# ==========================================
# Stage 2: Production
# ==========================================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Run as non-root user for security
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy only the source code needed for execution
COPY --chown=appuser:appuser src/ src/

EXPOSE 8000

# Start FastAPI application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
