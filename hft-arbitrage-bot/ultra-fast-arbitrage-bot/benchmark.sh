#!/bin/bash
echo "⚡ Running performance benchmarks..."

# Build with maximum optimization
cargo build --release

# Run benchmarks
echo "Testing scan speed..."
time ./target/release/ultra-fast-arbitrage-bot --benchmark

echo "Performance test completed!"
