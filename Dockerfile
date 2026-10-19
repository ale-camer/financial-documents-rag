FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy packaging and dependencies
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir .

# Copy source code and entrypoint
COPY src/ ./src/
COPY entrypoint.sh ./

RUN chmod +x /app/entrypoint.sh

ENV PORT=8000
EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
