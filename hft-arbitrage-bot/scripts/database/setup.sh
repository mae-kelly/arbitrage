#!/bin/bash
# Database setup script

echo "🗄️ Setting up production databases..."

# PostgreSQL setup
docker run -d \
  --name arbitrage-postgres \
  -e POSTGRES_DB=arbitrage \
  -e POSTGRES_USER=arbitrage \
  -e POSTGRES_PASSWORD=arbitrage123 \
  -p 5432:5432 \
  timescale/timescaledb:latest-pg14

# Redis setup
docker run -d \
  --name arbitrage-redis \
  -p 6379:6379 \
  redis:7-alpine \
  redis-server --appendonly yes

# Wait for services
echo "⏳ Waiting for databases to start..."
sleep 10

# Run migrations
export DATABASE_URL="postgresql://arbitrage:arbitrage123@localhost:5432/arbitrage"
sqlx migrate run

echo "✅ Databases ready!"
echo "PostgreSQL: postgresql://arbitrage:arbitrage123@localhost:5432/arbitrage"
echo "Redis: redis://localhost:6379"
