#!/bin/bash

echo "🔥 BUILDING M1 GPU ONLY ARBITRAGE BOT"
echo "====================================="
echo "⚡ NO CPU fallback - GPU REQUIRED"

# Verify Apple Silicon
if [[ $(uname -m) != "arm64" ]]; then
    echo "❌ FATAL: Apple Silicon REQUIRED"
    echo "   This is M1 GPU ONLY - no CPU fallback"
    exit 1
fi

# Set M1 GPU-only build flags
export RUSTFLAGS="-C target-cpu=apple-m1 -C target-feature=+neon,+fp-armv8,+apple-a14"
export RUSTFLAGS="$RUSTFLAGS -C link-arg=-framework -C link-arg=Metal"
export RUSTFLAGS="$RUSTFLAGS -C link-arg=-framework -C link-arg=MetalPerformanceShaders"

echo "🔨 Building M1 GPU-only bot..."
echo "🚫 CPU fallback: DISABLED"

cargo build --release --target aarch64-apple-darwin

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ M1 GPU ONLY BUILD SUCCESS"
    echo "🔥 GPU-exclusive arbitrage bot ready"
    echo "🚫 NO CPU fallback available"
    echo ""
    echo "🚀 Start with: ./start-m1-gpu-only.sh"
else
    echo "❌ Build failed!"
fi
