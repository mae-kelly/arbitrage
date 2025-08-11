#!/bin/bash
echo "🔑 Interactive API Key Setup"
echo "============================"

# Check if .env exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists. Backing up to .env.backup"
    cp .env .env.backup
fi

# Copy template
cp .env.example .env

echo ""
echo "Please enter your API keys (press Enter to skip):"
echo ""

# Coinbase setup
echo "📊 COINBASE (Recommended for US users):"
read -p "Coinbase API Key: " coinbase_key
read -p "Coinbase Secret: " coinbase_secret
read -p "Coinbase Passphrase: " coinbase_passphrase

if [ ! -z "$coinbase_key" ]; then
    sed -i "s/your_coinbase_api_key_here/$coinbase_key/" .env
    sed -i "s/your_coinbase_secret_here/$coinbase_secret/" .env
    sed -i "s/your_coinbase_passphrase_here/$coinbase_passphrase/" .env
    echo "✅ Coinbase configured"
fi

echo ""

# Kraken setup
echo "🐙 KRAKEN:"
read -p "Kraken API Key: " kraken_key
read -p "Kraken Private Key: " kraken_private

if [ ! -z "$kraken_key" ]; then
    sed -i "s/your_kraken_api_key_here/$kraken_key/" .env
    sed -i "s/your_kraken_private_key_here/$kraken_private/" .env
    echo "✅ Kraken configured"
fi

echo ""

# KuCoin setup
echo "🎯 KUCOIN (High volume exchange):"
read -p "KuCoin API Key: " kucoin_key
read -p "KuCoin Secret: " kucoin_secret
read -p "KuCoin Passphrase: " kucoin_passphrase

if [ ! -z "$kucoin_key" ]; then
    sed -i "s/your_kucoin_api_key_here/$kucoin_key/" .env
    sed -i "s/your_kucoin_secret_here/$kucoin_secret/" .env
    sed -i "s/your_kucoin_passphrase_here/$kucoin_passphrase/" .env
    echo "✅ KuCoin configured"
fi

echo ""

# Ethereum setup
echo "🔗 ETHEREUM/WEB3 (For flash loans):"
read -p "Infura Project ID (or other RPC URL): " infura_id
read -s -p "Private Key (for flash loan execution): " private_key
echo ""

if [ ! -z "$infura_id" ]; then
    sed -i "s/YOUR_INFURA_KEY/$infura_id/" .env
    echo "✅ Ethereum RPC configured"
fi

if [ ! -z "$private_key" ]; then
    sed -i "s/your_ethereum_private_key_here/$private_key/" .env
    echo "✅ Private key configured"
fi

echo ""
echo "🎉 API key setup completed!"
echo "💡 You can manually edit .env file to add more exchanges"
echo "🚀 Run './start.sh' to start the bot"
