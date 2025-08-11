#!/bin/bash

echo "🔥 STARTING M1 GPU ONLY ARBITRAGE BOT"
echo "===================================="

BINARY="./target/aarch64-apple-darwin/release/m1-gpu-only-arbitrage-bot"

if [ ! -f "$BINARY" ]; then
    echo "🔨 Building M1 GPU-only bot..."
    ./build-m1-gpu-only.sh
fi

# Verify Apple Silicon
if [[ $(uname -m) != "arm64" ]]; then
    echo "❌ FATAL: Apple Silicon REQUIRED"
    exit 1
fi

# Set M1 GPU environment
export METAL_DEVICE_WRAPPER_TYPE=1
export MTL_HUD_ENABLED=1

echo "🔥 M1 GPU: REQUIRED"
echo "🚫 CPU fallback: DISABLED"
echo "⚡ Starting GPU-exclusive mode..."
echo ""

exec "$BINARY"
