#!/bin/bash

# First, let's clean up and start fresh
docker-compose down
docker system prune -f

# Create a minimal working Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
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

EXPOSE 8000

# Use a simple command that will show us what's happening
CMD ["python", "-c", "print('Bot container started'); import time; time.sleep(10); exec(open('src/main.py').read())"]
EOF

# Create a simpler docker-compose.yml
cat > docker-compose.yml << 'EOF'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

  clickhouse:
    image: clickhouse/clickhouse-server:23.8
    ports:
      - "9000:9000"
      - "8123:8123"
    environment:
      - CLICKHOUSE_DB=arbitrage
    restart: unless-stopped

  arbitrage-bot:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - CLICKHOUSE_URL=clickhouse://clickhouse:9000
      - PYTHONPATH=/app
    depends_on:
      - redis
      - clickhouse
    volumes:
      - ./logs:/app/logs
    restart: "no"
EOF

# Create a minimal test version of main.py to verify the container works
cat > src/test_main.py << 'EOF'
import sys
import os
sys.path.insert(0, '/app')

print("Testing container startup...")
print(f"Python path: {sys.path}")
print(f"Working directory: {os.getcwd()}")
print(f"Directory contents: {os.listdir('.')}")

try:
    import redis
    print("Redis import: OK")
except Exception as e:
    print(f"Redis import failed: {e}")

try:
    import torch
    print("PyTorch import: OK")
except Exception as e:
    print(f"PyTorch import failed: {e}")

try:
    import pandas
    print("Pandas import: OK")
except Exception as e:
    print(f"Pandas import failed: {e}")

print("Container test completed successfully!")
EOF

echo "Created fixed Docker configuration"
echo ""
echo "Now run these commands:"
echo "1. docker-compose build"
echo "2. docker-compose up redis clickhouse"
echo "3. Wait 10 seconds, then: docker-compose up arbitrage-bot"
echo ""
echo "If that works, we'll add the real code step by step"