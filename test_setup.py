#!/usr/bin/env python3
import json
from web3 import Web3

print("🧪 Testing MEV Bot Setup...")

# Load keys
try:
    with open('.keys.json', 'r') as f:
        keys = json.load(f)
    print("✅ Keys loaded successfully")
    print(f"   Main wallet: {keys['main']['address']}")
except Exception as e:
    print(f"❌ Failed to load keys: {e}")

# Test Web3
try:
    w3 = Web3(Web3.HTTPProvider('https://eth-mainnet.g.alchemy.com/v2/demo'))
    if w3.is_connected():
        print(f"✅ Connected to Ethereum")
        print(f"   Latest block: {w3.eth.block_number:,}")
        print(f"   Gas price: {w3.eth.gas_price / 10**9:.2f} gwei")
except Exception as e:
    print(f"❌ Web3 connection failed: {e}")

print("\n📋 Next Steps:")
print("1. Get API keys from:")
print("   • https://www.alchemy.com/")
print("   • https://docs.flashbots.net/")
print("2. Add keys to .env file")
print("3. Fund main wallet with ETH")
print("4. Run: python3 core/engine.py")
