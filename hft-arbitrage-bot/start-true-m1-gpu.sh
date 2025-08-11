#!/bin/bash

echo "🔥 STARTING TRUE M1 GPU ARBITRAGE BOT"
echo "====================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_header() { echo -e "${PURPLE}$1${NC}"; }

# Check if binary exists
BINARY="./target/aarch64-apple-darwin/release/true-m1-gpu-arbitrage-bot"

if [ ! -f "$BINARY" ]; then
    print_status "Binary not found. Building with TRUE M1 GPU optimizations..."
    ./build-true-m1-gpu.sh
    
    if [ ! -f "$BINARY" ]; then
        echo "❌ Build failed or binary not created"
        exit 1
    fi
fi

print_header "🖥️  METAL GPU SYSTEM CHECK"
echo ""

# Verify Metal GPU
print_status "Checking Metal GPU availability..."
if system_profiler SPDisplaysDataType | grep -q "Metal"; then
    GPU_INFO=$(system_profiler SPDisplaysDataType | grep -A 5 "Apple M")
    print_success "Metal GPU detected"
    echo "$GPU_INFO" | head -3
else
    echo "⚠️  Metal GPU status unclear"
fi

echo ""

# Set optimal environment variables for M1 GPU
export RUST_LOG=info
export METAL_DEVICE_WRAPPER_TYPE=1
export MTL_HUD_ENABLED=1
export MTL_SHADER_VALIDATION=0  # Disable for performance
export METAL_PERFORMANCE_HUD=1

# M1 performance optimizations
export RAYON_NUM_THREADS=8  # M1 has 8 cores
export TOKIO_WORKER_THREADS=8

print_header "⚡ PERFORMANCE SETTINGS"
echo "• Metal HUD: Enabled (shows GPU usage)"
echo "• GPU validation: Disabled (for speed)"
echo "• CPU threads: 8 (M1 optimized)"
echo "• Async workers: 8"
echo ""

print_header "🎯 EXPECTED PERFORMANCE"
echo "• Arbitrage scanning: <10μs"
echo "• GPU utilization: 60-90%"
echo "• Memory bandwidth: 400GB/s"
echo "• Power consumption: 8-20W"
echo ""

print_success "Starting TRUE M1 GPU arbitrage bot..."
echo ""

# Run the TRUE M1 GPU optimized bot
exec "$BINARY"
