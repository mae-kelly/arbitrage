#!/bin/bash
echo "Fixing RPC provider issues..."
sed -i '' 's/w3 = self.rpc_manager.get_best_provider()/w3 = self.rpc_manager.w3/g' main.py
sed -i '' 's/\.get_best_provider()\.eth/.w3.eth/g' main.py
echo "✓ RPC fixed"
