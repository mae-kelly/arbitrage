#!/bin/bash
echo "Direct fix for Web3 connection..."

# Backup main.py
cp main.py main.py.backup

# Create a patch that directly uses Web3
cat > patch_main.py << 'PATCH'
import sys
import re

with open('main.py', 'r') as f:
    content = f.read()

# Find and replace the balance check lines
content = re.sub(
    r'w3 = self\.rpc_manager.*',
    'from web3 import Web3; w3 = Web3(Web3.HTTPProvider(f"https://eth-sepolia.g.alchemy.com/v2/{self.config.ALCHEMY_API_KEY}"))',
    content
)

with open('main.py', 'w') as f:
    f.write(content)
PATCH

python3 patch_main.py
rm patch_main.py
echo "✓ Direct connection established"
