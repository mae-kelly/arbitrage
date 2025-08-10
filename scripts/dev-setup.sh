#!/bin/bash
set -e

echo "🔄 Setting up development environment..."

# Install Python dependencies (basic setup)
pip install --upgrade pip wheel setuptools

# Install Rust dependencies
echo "📦 Installing Rust tools..."
cargo install cargo-watch cargo-expand

echo "✅ Development environment ready!"
echo "Run './activate.sh' to activate the environment"
