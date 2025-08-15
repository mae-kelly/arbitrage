#!/bin/bash
echo "🔨 Building Realistic Arbitrage Bot..."

if ! command -v cargo &> /dev/null; then
    echo "❌ Rust not found. Install from: https://rustup.rs/"
    exit 1
fi

cargo build --release

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo "🚀 Run with: ./run.sh"
else
    echo "❌ Build failed!"
    exit 1
fi
