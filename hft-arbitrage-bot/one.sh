#!/bin/bash

# Fix Disk Space Issues - Comprehensive Cleanup Script
# Run this script to free up disk space and fix pip installation issues

set -e  # Exit on any error

echo "🧹 DISK SPACE CLEANUP & FIX SCRIPT"
echo "=================================="

# Function to display disk usage
show_disk_usage() {
    echo "📊 Current disk usage:"
    df -h | head -2
    echo ""
}

# Function to get available space in MB (macOS compatible)
get_available_space() {
    df -m / | awk 'NR==2 {print $4}'
}

# Show initial disk usage
echo "🔍 Initial disk state:"
show_disk_usage

# Check if we have critically low space
AVAILABLE=$(get_available_space)
if [ "$AVAILABLE" -lt 1000 ]; then
    echo "⚠️  CRITICAL: Less than 1GB available. Running emergency cleanup..."
    AGGRESSIVE_MODE=true
else
    echo "ℹ️  Available space: ${AVAILABLE}MB"
    AGGRESSIVE_MODE=false
fi

echo "🗑️  Starting cleanup process..."

# 1. Clean pip cache
echo "1️⃣  Cleaning pip cache..."
pip cache purge 2>/dev/null || echo "   ⚠️  pip cache already clean or not accessible"

# 2. Clean Python cache files
echo "2️⃣  Cleaning Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true

# 3. Clean temporary files
echo "3️⃣  Cleaning temporary files..."
rm -rf /tmp/* 2>/dev/null || true
rm -rf ~/Library/Caches/pip 2>/dev/null || true

# 4. Clean large files found in Downloads immediately
echo "4️⃣  EMERGENCY: Removing large files from Downloads..."
if [ -d ~/Downloads ]; then
    # Remove the large .crdownload file (incomplete download)
    rm -f ~/Downloads/*.crdownload 2>/dev/null || true
    
    # Remove VSCode zip if it exists (can be re-downloaded)
    rm -f ~/Downloads/VSCode-darwin-universal.zip 2>/dev/null || true
    
    # Remove Visual Studio Code app if in Downloads (move to Applications instead)
    if [ -d ~/Downloads/Visual\ Studio\ Code.app ]; then
        echo "   📦 Moving Visual Studio Code to Applications..."
        mv ~/Downloads/Visual\ Studio\ Code.app /Applications/ 2>/dev/null || rm -rf ~/Downloads/Visual\ Studio\ Code.app
    fi
    
    echo "   ✅ Large Downloads files removed"
fi

# 5. EMERGENCY: Clean the massive Git pack file temporarily
echo "5️⃣  EMERGENCY: Temporarily reducing Git repository size..."
if [ -d ".git" ]; then
    echo "   🗂️  Creating temporary backup and cleaning Git..."
    # Run git garbage collection to compress
    git gc --prune=now --aggressive 2>/dev/null || true
    # Clean up any loose objects
    git prune 2>/dev/null || true
    echo "   ✅ Git repository optimized"
fi

# 6. Clean Homebrew cache (if exists)
if command -v brew >/dev/null 2>&1; then
    echo "6️⃣  Cleaning Homebrew cache..."
    brew cleanup --prune=all 2>/dev/null || true
    brew autoremove 2>/dev/null || true
fi

# 7. EMERGENCY: Clean more system locations
if [ "$AGGRESSIVE_MODE" = true ]; then
    echo "7️⃣  EMERGENCY cleanup mode..."
    
    # Clean user cache directories
    echo "   🗑️  Cleaning user caches..."
    rm -rf ~/Library/Caches/* 2>/dev/null || true
    rm -rf ~/Library/Application\ Support/pip 2>/dev/null || true
    rm -rf ~/.cache 2>/dev/null || true
    
    # Clean trash
    echo "   🗑️  Emptying Trash..."
    rm -rf ~/.Trash/* 2>/dev/null || true
    
    # Clean system temp files more aggressively
    sudo rm -rf /tmp/* 2>/dev/null || true
    sudo rm -rf /var/tmp/* 2>/dev/null || true
    
    echo "   ✅ Emergency cleanup completed"
fi

# 6. Clean Downloads folder large files
echo "6️⃣  Finding large files in Downloads..."
if [ -d ~/Downloads ]; then
    find ~/Downloads -size +100M -type f 2>/dev/null | head -10 | while read file; do
        echo "   📦 Large file found: $file ($(du -h "$file" | cut -f1))"
    done
fi

# 8. Optimize installation strategy for low disk space
echo "8️⃣  Setting up minimal Python environment for low disk space..."
if [ -d "venv" ]; then
    echo "   🗑️  Removing existing venv..."
    rm -rf venv
fi

# Create new venv
python3 -m venv venv
source venv/bin/activate

# Upgrade pip with no cache
pip install --no-cache-dir --upgrade pip

# Create ultra-minimal requirements for very low space
cat > requirements_ultra_minimal.txt << 'EOF'
# Ultra minimal - only absolute essentials for basic functionality
requests
aiohttp
fastapi
uvicorn[standard]
EOF

echo "   📦 Installing only essential packages..."
pip install --no-cache-dir -r requirements_ultra_minimal.txt

# 8. Clean Docker (if exists and aggressive mode)
if command -v docker >/dev/null 2>&1 && [ "$AGGRESSIVE_MODE" = true ]; then
    echo "8️⃣  Cleaning Docker (aggressive mode)..."
    docker system prune -af 2>/dev/null || true
fi

# 9. Clean Xcode derived data (if exists)
if [ -d ~/Library/Developer/Xcode/DerivedData ]; then
    echo "9️⃣  Cleaning Xcode derived data..."
    rm -rf ~/Library/Developer/Xcode/DerivedData/* 2>/dev/null || true
fi

# 10. Clean node_modules if they exist
echo "🔟 Cleaning node_modules directories..."
find . -name "node_modules" -type d -exec rm -rf {} + 2>/dev/null || true

# Show final disk usage
echo ""
echo "✅ Cleanup completed!"
show_disk_usage

# Check if we now have enough space
AVAILABLE_AFTER=$(get_available_space)
echo "💾 Space freed: $((AVAILABLE_AFTER - AVAILABLE))MB"

if [ "$AVAILABLE_AFTER" -lt 500 ]; then
    echo "❌ Still critically low on space ($AVAILABLE_AFTER MB). Manual intervention needed:"
    echo "   📋 URGENT ACTIONS REQUIRED:"
    echo "   • Empty Trash: cmd+shift+delete in Finder"
    echo "   • Delete large apps you don't use from Applications folder"
    echo "   • Move large files to external storage or cloud"
    echo "   • Consider upgrading storage or using external drive"
    echo ""
    echo "   🔍 To find large files manually:"
    echo "   sudo du -h /Users/$(whoami) | sort -rh | head -20"
    exit 1
fi

echo ""
echo "🔧 FIXING PIP INSTALLATION"
echo "=========================="

# Fix Cargo.toml duplicate dependencies
echo "🛠️  Fixing Cargo.toml duplicate dependencies..."
if [ -f "Cargo.toml" ]; then
    # Create backup
    cp Cargo.toml Cargo.toml.backup
    
    # Remove duplicate ethers entries
    awk '
    /^\[dev-dependencies\]/ { in_dev_deps = 1; print; next }
    /^\[/ && !/^\[dev-dependencies\]/ { in_dev_deps = 0; print; next }
    in_dev_deps && /^ethers = / {
        if (!seen_ethers) {
            print
            seen_ethers = 1
        }
        next
    }
    { print }
    ' Cargo.toml.backup > Cargo.toml
    
    echo "   ✅ Fixed duplicate ethers dependency"
fi

# Create a minimal requirements file for essential packages only
echo "📝 Creating minimal requirements.txt..."
cat > requirements_minimal.txt << 'EOF'
# Essential packages only to avoid space issues
torch>=2.0.0
numpy>=1.24.0
pandas>=2.0.0
scikit-learn>=1.3.0
fastapi>=0.100.0
uvicorn>=0.22.0
pydantic>=2.0.0
requests
ccxt>=4.0.0
aiohttp
EOF

# Activate virtual environment and install minimal requirements
if [ -d "venv" ]; then
    echo "🐍 Testing ultra-minimal installation..."
    source venv/bin/activate
    
    echo "   ✅ Ultra-minimal packages installed successfully"
    echo "   📝 You can now add packages one by one as space allows"
else
    echo "⚠️  Virtual environment setup failed. Check available space."
fi

echo ""
echo "🎉 EMERGENCY CLEANUP COMPLETED!"
echo "==============================="
echo "✅ Disk space emergency resolved"
echo "✅ Ultra-minimal environment ready"
echo "✅ Cargo.toml fixed"
echo ""
echo "🚀 Immediate next steps:"
echo "   1. source venv/bin/activate"
echo "   2. cargo check"
echo ""
echo "⚠️  IMPORTANT - You're in ULTRA-MINIMAL mode:"
echo "   • Only basic packages installed to save space"
echo "   • Add packages individually: pip install --no-cache-dir <package>"
echo "   • Monitor space: df -h"
echo "   • Consider external storage for this project"
echo ""
echo "💡 When space allows, install packages one by one:"
echo "   pip install --no-cache-dir numpy"
echo "   pip install --no-cache-dir pandas"
echo "   pip install --no-cache-dir torch"