#!/bin/bash
# quick_start.sh - Quick start MEV bot

source venv/bin/activate
source .env

echo "🚀 Quick Start MEV Bot"
echo "======================"
echo ""
echo "1) Safe Mode (Local Fork)"
echo "2) Testnet Mode"
echo "3) Live Mode (MAINNET)"
echo -n "Choose mode: "
read -r mode

case $mode in
    1)
        echo "Starting local fork..."
        npx hardhat node --fork $RPC_URL &
        FORK_PID=$!
        sleep 5
        RPC_URL="http://localhost:8545"
        python3 run_bot.py
        kill $FORK_PID
        ;;
    2)
        RPC_URL="https://eth-sepolia.g.alchemy.com/v2/$ALCHEMY_KEY"
        python3 run_bot.py
        ;;
    3)
        echo "⚠️  MAINNET MODE - REAL MONEY"
        echo -n "Type 'CONFIRM' to proceed: "
        read -r confirm
        if [[ "$confirm" == "CONFIRM" ]]; then
            python3 run_bot.py
        fi
        ;;
esac
