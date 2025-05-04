# Stage 1: Build environment
FROM python:3.13-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    build-base

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install required packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime environment
FROM python:3.13-alpine

WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache libffi openssl wget

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY UK_US_Word_Analyzer_API.py .  
COPY us_dict.txt uk_dict.txt ./    

# Set environment variables
ENV US_DICT_PATH=/app/us_dict.txt
ENV UK_DICT_PATH=/app/uk_dict.txt

# Create non-root user
RUN adduser -D -u 10001 appuser && \
    chown -R appuser:appuser /app
USER 10001

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:8000/analyze || exit 1

EXPOSE 8000

# Start FastAPI app
CMD ["uvicorn", "UK_US_Word_Analyzer_API:app", "--host", "0.0.0.0", "--port", "8000"]
