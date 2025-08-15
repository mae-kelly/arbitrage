#!/bin/bash
echo "🚀 Starting Realistic Arbitrage Bot..."

if [ ! -f "./target/release/arbitrage-bot" ]; then
    echo "🔨 Building first..."
    ./build.sh
fi

export RUST_LOG=info
./target/release/arbitrage-bot
