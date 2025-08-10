#!/bin/bash

echo "⚡ STARTING LIGHTNING ARBITRAGE SYSTEM"
echo "======================================"

# Check virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d "venv" ]; then
        echo "Activating virtual environment..."
        source venv/bin/activate
    fi
fi

# Check Redis
if command -v redis-server &> /dev/null; then
    if ! pgrep -x "redis-server" > /dev/null; then
        echo "Starting Redis..."
        redis-server --daemonize yes
    fi
fi

# Build the project
echo "Building Rust components..."
if cargo build --release 2>/dev/null; then
    echo "✅ Build successful"
else
    echo "⚠️  Build failed, trying to fix..."
    cargo build 2>&1 | head -20
fi

# Run the system
echo ""
echo "🚀 Starting arbitrage engine..."
cargo run --release 2>/dev/null || cargo run

# Keep running
trap "echo 'Shutting down...'; exit" INT TERM
wait
