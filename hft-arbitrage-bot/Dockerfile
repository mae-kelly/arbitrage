FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Create directory structure
RUN mkdir -p src/core src/ai src/infrastructure src/contracts logs

# Create __init__.py files
RUN touch src/__init__.py \
    src/core/__init__.py \
    src/ai/__init__.py \
    src/infrastructure/__init__.py \
    src/contracts/__init__.py

# Copy source code
COPY src/ ./src/
COPY config.json ./

# Set Python path and environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Run the main application
CMD ["python", "src/main.py"]
