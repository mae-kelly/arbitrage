#!/bin/bash
echo "🚀 Starting Ultra-Fast Arbitrage Bot..."

# Set performance environment variables
export RUST_LOG=info
export RAYON_NUM_THREADS=$(nproc)

# Run with maximum performance settings
cargo run --release
