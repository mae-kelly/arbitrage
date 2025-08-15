#!/bin/bash
# Setup environment for real trading

echo "🔧 Setting up real trading environment..."

# Create necessary directories
mkdir -p data/logs
mkdir -p data/backups
mkdir -p config/exchanges

# Set proper permissions
chmod 600 config/trading_config.json
chmod 700 config/

echo "📝 Please set your API keys:"
echo ""
echo "Environment variables:"
echo "export COINBASE_API_KEY='your_key'"
echo "export COINBASE_SECRET='your_secret'"
echo "export COINBASE_PASSPHRASE='your_passphrase'"
echo ""
echo "Or edit config/trading_config.json"
echo ""
echo "⚠️  SECURITY:"
echo "- Never commit API keys to version control"
echo "- Use sandbox/testnet for testing"
echo "- Start with small position sizes"
echo ""
echo "✅ Environment setup complete"
