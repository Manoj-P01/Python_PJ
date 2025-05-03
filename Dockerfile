# Stage 1: Build environment
FROM python:3.14.0-rc-alpine3.19 as builder

WORKDIR /app

# Install system dependencies (required for docx2txt and others)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime environment
FROM python:3.14.0-rc-alpine3.19

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application files
COPY . .

# Copy dictionaries (adjust paths as needed)
COPY us_dict.txt uk_dict.txt ./

# Set environment variables for dictionary paths
ENV US_DICT_PATH=/app/us_dict.txt
ENV UK_DICT_PATH=/app/uk_dict.txt

# Run as non-root user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
