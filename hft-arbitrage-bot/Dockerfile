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
