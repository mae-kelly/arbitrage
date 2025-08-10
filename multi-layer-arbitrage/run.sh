#!/bin/bash

echo "🔨 Building Multi-Layer Arbitrage System..."
cargo build --release

echo "🚀 Starting arbitrage bot..."
echo ""
echo "Configuration:"
echo "  • L1 CEX: Binance, Coinbase, Kraken, OKX, Bybit"
echo "  • L2 Networks: Arbitrum, Optimism, Polygon, Base"
echo "  • DEX: Uniswap V3, SushiSwap, Curve"
echo "  • Scan Interval: 100ms"
echo "  • Min Profit: 0.05%"
echo ""

# Set environment variables
export RUST_LOG=info
export RUST_BACKTRACE=1

# Run the bot
./target/release/multi-layer-arbitrage
