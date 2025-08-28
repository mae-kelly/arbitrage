#!/bin/bash
# quick_start.sh

set -e

echo "======================================"
echo "    DeFi Bot Quick Start Setup        "
echo "======================================"
echo ""

chmod +x *.sh

echo "This script will:"
echo "1. Set up testnet configuration"
echo "2. Deploy smart contracts"
echo "3. Start the trading bot"
echo ""
read -p "Continue? (y/n): " CONTINUE

if [ "$CONTINUE" != "y" ]; then
    exit 0
fi

echo ""
echo "Step 1: Setting up testnet configuration..."
echo "==========================================="
./setup_testnet.sh

echo ""
echo "Step 2: Deploying smart contracts..."
echo "====================================="
./deploy_contracts.sh

echo ""
echo "Step 3: Starting the trading bot..."
echo "===================================="
./run_testnet.sh