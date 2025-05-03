# Stage 1: Build environment
FROM python:3.13-alpine AS builder

WORKDIR /app

# Install system dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    python3-dev

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime environment
FROM python:3.13-alpine

WORKDIR /app

# Copy virtual environment
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application files
COPY . .

# Copy dictionaries
COPY us_dict.txt uk_dict.txt ./

# Set environment variables
ENV US_DICT_PATH=/app/us_dict.txt
ENV UK_DICT_PATH=/app/uk_dict.txt

# Create non-root user with ID between 10000-20000
RUN adduser -D -u 10001 appuser && \
    chown -R appuser:appuser /app

USER 10001

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
