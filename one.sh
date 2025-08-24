#!/bin/bash

echo "🚀 Quick MEV Bot Setup"
echo "======================"

# Use the existing venv
source venv/bin/activate

# Install only what works
pip install web3 eth-account

# Generate wallets using a simple script
python3 << 'EOF'
from eth_account import Account
import json

print("Generating wallets...")

# Create wallets
wallets = {}
for name in ['main', 'flashbots', 'validator']:
    account = Account.create()
    wallets[name] = {
        'address': account.address,
        'private_key': account.key.hex()
    }
    print(f"  {name}: {account.address}")

# Save to file
with open('.keys.json', 'w') as f:
    json.dump(wallets, f, indent=2)

print("\n✅ Wallets saved to .keys.json")
print("⚠️  KEEP THIS FILE SECURE!")

# Test connection
from web3 import Web3
w3 = Web3(Web3.HTTPProvider('https://eth-mainnet.g.alchemy.com/v2/demo'))
print(f"\n📊 Ethereum Status:")
print(f"  Connected: {w3.is_connected()}")
print(f"  Latest block: {w3.eth.block_number:,}")
print(f"  Gas price: {w3.eth.gas_price / 10**9:.1f} gwei")
EOF

echo ""
echo "✅ Done! Next steps:"
echo "1. Get API keys from Alchemy.com"
echo "2. Fund your main wallet with ETH"
echo "3. Never share .keys.json!"