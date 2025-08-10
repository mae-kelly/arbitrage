#!/bin/bash

echo "🛑 EMERGENCY STOP - Shutting down arbitrage bot"

docker-compose -f docker-compose.prod.yml stop arbitrage-bot

echo "💰 Withdrawing all funds to safe wallet..."
npx hardhat run scripts/emergency_withdraw.ts --network mainnet

echo "📊 Final profit report..."
curl -s http://localhost:3030/stats | jq .

echo "✅ Emergency stop completed"
