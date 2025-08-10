#!/bin/bash

echo "Starting Crypto Arbitrage Bot..."

source venv/bin/activate

echo "Checking environment..."
if [ ! -f ".env" ]; then
    echo "Error: .env file not found. Please configure your API keys."
    exit 1
fi

echo "Starting Redis..."
redis-server --daemonize yes

echo "Training ML models..."
cd ml && python train.py &
ML_PID=$!

echo "Compiling contracts..."
npx hardhat compile

echo "Starting TypeScript monitor..."
npm run monitor &
TS_PID=$!

echo "Starting Rust core engine..."
cd core && cargo run --release &
RUST_PID=$!

echo "Bot is running!"
echo "ML Process: $ML_PID"
echo "TypeScript Monitor: $TS_PID"
echo "Rust Core: $RUST_PID"

trap "kill $ML_PID $TS_PID $RUST_PID; redis-cli shutdown" EXIT

wait
