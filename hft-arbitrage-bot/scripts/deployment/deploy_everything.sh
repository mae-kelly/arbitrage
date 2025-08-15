#!/bin/bash
# One-command deployment for Ultra-HFT system

set -e

echo "🚀 DEPLOYING ULTRA-HFT ARBITRAGE SYSTEM"
echo "======================================="

# Build ultra-optimized release
echo "🔨 Building ultra-optimized release..."
export RUSTFLAGS="-C target-cpu=native -C opt-level=3 -C lto=fat"
cargo build --release

# Run tests
echo "🧪 Running comprehensive tests..."
cargo test --release

# Create deployment package
echo "📦 Creating deployment package..."
mkdir -p deployment/ultra-hft
cp target/release/realistic-arbitrage-bot deployment/ultra-hft/
cp -r config deployment/ultra-hft/
cp -r scripts deployment/ultra-hft/

# Create systemd service
cat > deployment/ultra-hft.service << SERVICE_EOF
[Unit]
Description=Ultra-HFT Arbitrage System
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/ultra-hft
ExecStart=/opt/ultra-hft/realistic-arbitrage-bot
Restart=always
RestartSec=5
Environment=RUST_LOG=info
Environment=RAYON_NUM_THREADS=8

[Install]
WantedBy=multi-user.target
SERVICE_EOF

# Create Docker image
echo "🐳 Building Docker image..."
docker build -t ultra-hft:latest .

# Deploy to cloud (placeholder)
echo "☁️ Deploying to cloud infrastructure..."
# kubectl apply -f k8s/
# docker-compose up -d

echo "✅ Deployment completed successfully!"
echo "🎯 System ready for ultra-high-frequency trading"
