#!/bin/bash
# monitor_bot.sh

set -e

echo "======================================"
echo "     Bot Monitoring Dashboard         "
echo "======================================"
echo ""

if [ ! -f ".env.testnet" ]; then
    echo "❌ .env.testnet not found"
    exit 1
fi

source .env.testnet

REFRESH_INTERVAL=5
MONITOR_MODE=""

while [[ ! "$MONITOR_MODE" =~ ^[1-5]$ ]]; do
    echo "Select monitoring mode:"
    echo "1) Live Performance Metrics"
    echo "2) Transaction History"
    echo "3) Gas Tracker"
    echo "4) Position Monitor"
    echo "5) Error Log Viewer"
    read -p "Enter choice (1-5): " MONITOR_MODE
done

case $MONITOR_MODE in
    1)
        while true; do
            clear
            echo "======================================"
            echo "       Live Performance Metrics       "
            echo "======================================"
            echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
            echo ""
            
            python3 -c "
from web3 import Web3
import os
import json
import requests

w3 = Web3(Web3.HTTPProvider('${RPC_BASE}${ALCHEMY_API_KEY}'))

# Wallet Balance
balance = w3.eth.get_balance('${WALLET_ADDRESS}')
eth_balance = Web3.from_wei(balance, 'ether')
print(f'Wallet Balance: {eth_balance:.4f} ETH')

# Gas Price
gas_price = w3.eth.gas_price
gas_gwei = Web3.from_wei(gas_price, 'gwei')
print(f'Current Gas: {gas_gwei:.1f} Gwei')

# Block Number
block = w3.eth.block_number
print(f'Block Height: {block}')

# Network Status
latest_block = w3.eth.get_block('latest')
print(f'Block Time: {latest_block[\"timestamp\"]}')
print(f'Gas Used: {latest_block[\"gasUsed\"]:,} / {latest_block[\"gasLimit\"]:,}')
print(f'Network Load: {(latest_block[\"gasUsed\"]/latest_block[\"gasLimit\"]*100):.1f}%')
"
            
            if [ -f "logs/performance.json" ]; then
                echo ""
                echo "Bot Statistics:"
                cat logs/performance.json | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'Total Profit: \${data.get(\"total_profit\", 0):.2f}')
    print(f'Trades Executed: {data.get(\"trades_executed\", 0)}')
    print(f'Success Rate: {data.get(\"success_rate\", 0):.1f}%')
    print(f'Gas Spent: {data.get(\"gas_spent\", 0):.4f} ETH')
except:
    print('No data available')
"
            fi
            
            sleep $REFRESH_INTERVAL
        done
        ;;
        
    2)
        echo "Transaction History"
        echo "==================="
        echo ""
        
        python3 -c "
from web3 import Web3
import os

w3 = Web3(Web3.HTTPProvider('${RPC_BASE}${ALCHEMY_API_KEY}'))

# Get recent transactions
block = w3.eth.get_block('latest', full_transactions=True)
wallet = '${WALLET_ADDRESS}'.lower()

print('Recent Transactions:')
print('-' * 80)

for tx in block['transactions'][:20]:
    if tx['from'].lower() == wallet or (tx['to'] and tx['to'].lower() == wallet):
        value = Web3.from_wei(tx['value'], 'ether')
        gas_price = Web3.from_wei(tx['gasPrice'], 'gwei')
        print(f'Hash: {tx[\"hash\"].hex()[:10]}...')
        print(f'From: {tx[\"from\"][:10]}... To: {tx[\"to\"][:10] if tx[\"to\"] else \"Contract Creation\"}')
        print(f'Value: {value:.4f} ETH | Gas: {gas_price:.1f} Gwei')
        print('-' * 80)
"
        ;;
        
    3)
        while true; do
            clear
            echo "======================================"
            echo "          Gas Price Tracker           "
            echo "======================================"
            echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
            echo ""
            
            python3 -c "
from web3 import Web3
import os

w3 = Web3(Web3.HTTPProvider('${RPC_BASE}${ALCHEMY_API_KEY}'))

# Get fee history
fee_history = w3.eth.fee_history(20, 'latest', [10, 25, 50, 75, 90])

print('Gas Price Percentiles (Gwei):')
print('-' * 40)

for i, percentiles in enumerate(['10%', '25%', '50%', '75%', '90%']):
    values = [Web3.from_wei(block[i], 'gwei') for block in fee_history['reward'] if block]
    if values:
        avg = sum(values) / len(values)
        print(f'{percentiles:>5}: {avg:>6.1f} Gwei')

base_fee = Web3.from_wei(fee_history['baseFeePerGas'][-1], 'gwei')
print(f'\\nBase Fee: {base_fee:.1f} Gwei')

# Recommended gas prices
print('\\nRecommended Gas Prices:')
print(f'Slow:     {base_fee * 1.1:.1f} Gwei')
print(f'Standard: {base_fee * 1.5:.1f} Gwei')
print(f'Fast:     {base_fee * 2:.1f} Gwei')
"
            
            sleep $REFRESH_INTERVAL
        done
        ;;
        
    4)
        echo "Position Monitor"
        echo "================"
        echo ""
        
        python3 -c "
from web3 import Web3
import os
import json

w3 = Web3(Web3.HTTPProvider('${RPC_BASE}${ALCHEMY_API_KEY}'))

# Token addresses (testnet)
tokens = {
    'USDC': '0x94a9D9AC8a22534E3FaCa9F4e7F2E2cf85d5E4C8',
    'USDT': '0xaA8E23Fb1079EA71e0a56F48a2aA51851D8433D0',
    'DAI': '0xFF34B3d4Aee8ddCd6F9AFFFB6Fe49bD371b8a357',
    'WETH': '0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14'
}

# ERC20 ABI (minimal)
erc20_abi = json.loads('[{\"inputs\":[{\"name\":\"account\",\"type\":\"address\"}],\"name\":\"balanceOf\",\"outputs\":[{\"name\":\"\",\"type\":\"uint256\"}],\"type\":\"function\"},{\"inputs\":[],\"name\":\"decimals\",\"outputs\":[{\"name\":\"\",\"type\":\"uint8\"}],\"type\":\"function\"}]')

print('Token Balances:')
print('-' * 50)

# ETH Balance
eth_balance = w3.eth.get_balance('${WALLET_ADDRESS}')
print(f'ETH:  {Web3.from_wei(eth_balance, \"ether\"):>15.6f}')

# Token Balances
for symbol, address in tokens.items():
    try:
        contract = w3.eth.contract(address=address, abi=erc20_abi)
        balance = contract.functions.balanceOf('${WALLET_ADDRESS}').call()
        decimals = contract.functions.decimals().call()
        formatted = balance / (10 ** decimals)
        if formatted > 0:
            print(f'{symbol}: {formatted:>15.6f}')
    except:
        pass
"
        ;;
        
    5)
        echo "Error Log Viewer"
        echo "================"
        echo ""
        
        if [ -d "logs" ]; then
            echo "Recent Errors:"
            echo "--------------"
            find logs -name "*.log" -type f -exec grep -H "ERROR\|CRITICAL\|Exception" {} \; | tail -20
        else
            echo "No log directory found"
        fi
        ;;
esac