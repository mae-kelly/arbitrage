#!/bin/bash
echo "Fixing RPCManager access..."

# Fix main.py to use the correct RPC manager method
cat > temp_fix.py << 'PYFIX'
with open('main.py', 'r') as f:
    content = f.read()

# Replace all w3 references to use proper RPC manager
content = content.replace('self.rpc_manager.w3', 'Web3(Web3.HTTPProvider(self.config.RPC_URL))')
content = content.replace('w3 = self.rpc_manager.w3', 'w3 = Web3(Web3.HTTPProvider(self.config.RPC_URL))')

# Add Web3 import if not present
if 'from web3 import Web3' not in content:
    content = 'from web3 import Web3\n' + content

with open('main.py', 'w') as f:
    f.write(content)
PYFIX

python3 temp_fix.py
rm temp_fix.py
echo "✓ RPC Manager fixed"
