#!/bin/bash
# monitor.sh - Real-time MEV monitoring

source venv/bin/activate
source .env

while true; do
    clear
    echo "📊 MEV Bot Monitor - $(date)"
    echo "================================"
    
    # Check bot status
    if pgrep -f "run_bot.py" > /dev/null; then
        echo "🟢 Bot Status: RUNNING"
    else
        echo "🔴 Bot Status: STOPPED"
    fi
    
    # Show recent opportunities
    python3 -c "
from web3 import Web3
import json

w3 = Web3(Web3.HTTPProvider('$RPC_URL'))
if w3.is_connected():
    block = w3.eth.get_block('latest')
    print(f'\\nCurrent Block: {block.number:,}')
    print(f'Gas Price: {w3.eth.gas_price / 10**9:.2f} gwei')
    print(f'Transactions in Block: {len(block.transactions)}')
    
    # Calculate potential
    potential = len(block.transactions) * 0.001 * 2500
    print(f'\\nPotential Profit: \${potential:.2f}')
"
    
    sleep 5
done
