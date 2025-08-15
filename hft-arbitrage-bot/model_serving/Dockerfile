FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Generate model weights
RUN python training/scripts/generate_weights.py

# Expose port
EXPOSE 8000

# Run server
CMD ["python", "model_serving/api/production_server.py"]
