#!/bin/bash

echo "🚀 Building Ultra-Lightweight Bot (minimal dependencies)..."
echo "📦 Binary size will be ~2MB vs 50MB+ for full version"
echo ""

# Clean any existing builds
cargo clean

# Build with size optimization
cargo build --release

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Build successful!"
    echo "📊 Binary size: $(du -h target/release/ultra-fast-arbitrage | cut -f1)"
    echo ""
    echo "🚀 Starting Ultra-Fast Arbitrage Bot..."
    echo ""
    
    cargo run --release
else
    echo "❌ Build failed"
    echo "💾 Please free up more disk space and try again"
    echo ""
    echo "To free space:"
    echo "• Empty Trash"
    echo "• Clear Downloads folder"
    echo "• Remove old Docker images: docker system prune -a"
    echo "• Clear browser cache"
fi
