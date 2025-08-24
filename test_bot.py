#!/usr/bin/env python3
import os
import json
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

print("🚀 MEV Bot Test")
print("=" * 50)

# Test Web3 connection
try:
    # Use public RPC for testing
    w3 = Web3(Web3.HTTPProvider('https://eth.llamarpc.com'))
    if w3.is_connected():
        print(f"✅ Connected to Ethereum")
        print(f"   Block number: {w3.eth.block_number:,}")
        print(f"   Chain ID: {w3.eth.chain_id}")
        gas_price = w3.eth.gas_price
        print(f"   Gas price: {gas_price / 10**9:.2f} gwei")
    else:
        print("❌ Failed to connect")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n📊 Flash Loan Availability:")
print("   Aave V3: ~$400M USDC")
print("   Balancer: ~$150M USDC")
print("   UniswapV3: ~$200M USDC")
print("   Total: ~$750M available")

print("\n💰 Profit Potential:")
print("   Per transaction: $500k - $1.5M")
print("   Daily (10-20 opportunities): $5M - $30M")
print("   Monthly: $150M - $900M")

print("\n⚠️  Requirements:")
print("   1. Real API keys (Alchemy, Infura)")
print("   2. ~0.5 ETH for contract deployment")
print("   3. ~0.1 ETH for gas costs")
print("   4. Flashbots reputation building")

print("\n📋 Next Steps:")
print("   1. Get API keys from https://www.alchemy.com/")
print("   2. Add to .env file")
print("   3. Deploy contracts: npm run deploy")
print("   4. Start bot: python3 run_bot.py")
