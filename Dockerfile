FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy project configuration files
COPY pyproject.toml README.md ./
# Copy source code
COPY src/ src/

# Install the package and its dependencies
RUN pip install --no-cache-dir .

EXPOSE 8000

# Start FastAPI application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
