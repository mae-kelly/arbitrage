#!/usr/bin/env python3
import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

print("🧪 Testing MEV Strategies")
print("=" * 40)

w3 = Web3(Web3.HTTPProvider(os.getenv('RPC_URL')))

if w3.is_connected():
    print("✅ Connected to network")
    
    # Test sandwich detection
    print("\nTesting Sandwich Detection...")
    block = w3.eth.get_block('latest', full_transactions=True)
    
    dex_routers = {
        '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D': 'Uniswap V2',
        '0xE592427A0AEce92De3Edee1F18E0157C05861564': 'Uniswap V3'
    }
    
    opportunities = 0
    for tx in block['transactions']:
        if tx.get('to') in dex_routers:
            value = tx.get('value', 0) / 10**18
            if value > 0.1:
                opportunities += 1
                profit = value * 0.003 * 2500
                print(f"  Found: {dex_routers[tx['to']]} - ${profit:.2f} profit")
    
    if opportunities == 0:
        print("  No opportunities in current block")
    
    print(f"\nTotal opportunities: {opportunities}")
    print("✅ Test complete")
else:
    print("❌ Cannot connect to network")
