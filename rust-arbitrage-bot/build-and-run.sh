#!/bin/bash

echo "🦀 Building Rust Lightning Arbitrage Bot..."
echo ""

if ! command -v cargo &> /dev/null; then
    echo "❌ Rust not installed. Installing..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source ~/.cargo/env
fi

echo "🔧 Compiling with maximum optimizations..."
cargo build --release

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Build successful!"
    echo "🚀 Starting Lightning Arbitrage Bot..."
    echo ""
    cargo run --release
else
    echo "❌ Build failed"
    exit 1
fi
