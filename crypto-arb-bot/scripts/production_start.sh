#!/bin/bash

echo "🔥 Starting Production Arbitrage System"

if [ ! -f ".env" ]; then
    echo "❌ .env file not found! Copy .env.example and configure it."
    exit 1
fi

echo "📊 Starting monitoring stack..."
docker-compose -f docker-compose.prod.yml up -d prometheus grafana

echo "💾 Starting database..."
docker-compose -f docker-compose.prod.yml up -d db redis

echo "⏳ Waiting for database to be ready..."
sleep 10

echo "📈 Deploying contracts to mainnet..."
npx hardhat run scripts/deploy.ts --network mainnet

echo "🚀 Starting arbitrage bot..."
docker-compose -f docker-compose.prod.yml up -d arbitrage-bot

echo "✅ Production system started!"
echo "📊 Grafana: http://localhost:3000"
echo "📈 Prometheus: http://localhost:9090" 
echo "🔍 Bot API: http://localhost:3030/stats"
echo ""
echo "Monitor logs: docker-compose -f docker-compose.prod.yml logs -f arbitrage-bot"
