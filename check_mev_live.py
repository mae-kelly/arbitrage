# save as check_mev_live.py
from web3 import Web3
import asyncio

w3 = Web3(Web3.HTTPProvider('https://eth.llamarpc.com'))

print("🔍 Scanning for LIVE MEV Opportunities...")
print("=" * 50)

# Check current block
block = w3.eth.get_block('latest', full_transactions=True)
print(f"Block: {block.number}")
print(f"Transactions: {len(block.transactions)}")

# Look for DEX trades (potential sandwich targets)
uniswap_router = '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'
large_trades = []

for tx in block.transactions:
    # Check if it's a Uniswap trade
    if tx['to'] and tx['to'].lower() == uniswap_router.lower():
        value_eth = tx['value'] / 10**18
        if value_eth > 0.5:  # Trades over 0.5 ETH
            large_trades.append({
                'hash': tx['hash'].hex(),
                'value': value_eth,
                'gas': tx['gas'],
                'gasPrice': tx['gasPrice'] / 10**9
            })

print(f"\n💰 Found {len(large_trades)} potential sandwich targets:")
for trade in large_trades[:5]:
    potential_profit = trade['value'] * 0.003  # 0.3% profit estimate