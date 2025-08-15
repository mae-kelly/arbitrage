#!/bin/bash

# 🧹 ULTIMATE CLEANUP & SPACE RECOVERY
echo "🧹 FREEING DISK SPACE FOR STATE-OF-THE-ART ARBITRAGE BOT"
echo "========================================================="

# Clean Rust build artifacts
echo "🗑️  Cleaning Rust build cache..."
cargo clean
rm -rf target/
rm -rf ~/.cargo/registry/cache/
rm -rf ~/.cargo/git/db/

# Clean system caches
echo "🗑️  Cleaning system caches..."
sudo rm -rf /private/var/folders/*/T/*
sudo rm -rf /var/tmp/*
rm -rf ~/Library/Caches/*
rm -rf ~/.cache/*

# Clean Docker if installed
if command -v docker &> /dev/null; then
    echo "🐳 Cleaning Docker..."
    docker system prune -af --volumes 2>/dev/null || true
fi

# Clean Xcode/iOS simulators if present
if [ -d ~/Library/Developer/Xcode/DerivedData ]; then
    echo "📱 Cleaning Xcode cache..."
    rm -rf ~/Library/Developer/Xcode/DerivedData/*
fi

# Clean homebrew cache
if command -v brew &> /dev/null; then
    echo "🍺 Cleaning Homebrew..."
    brew cleanup -s 2>/dev/null || true
fi

# Clean npm cache
if command -v npm &> /dev/null; then
    echo "📦 Cleaning npm cache..."
    npm cache clean --force 2>/dev/null || true
fi

# Clean Python cache
echo "🐍 Cleaning Python cache..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# Empty trash
echo "🗑️  Emptying trash..."
rm -rf ~/.Trash/*

# Show disk space
echo ""
echo "💾 DISK SPACE AFTER CLEANUP:"
df -h | head -2

echo ""
echo "✅ CLEANUP COMPLETE!"
echo "🚀 Ready to build state-of-the-art arbitrage bot!"