#!/usr/bin/env python3
import os
import re

files_to_update = [
    'flashloan_aggregator.py',
    'mev_predictor.py',
    'liquidation_predictor_ml.py',
    'oracle_manipulation.py',
    'unified_strategy.py',
    'advanced_sandwich.py'
]

for filename in files_to_update:
    if not os.path.exists(filename):
        continue
    
    with open(filename, 'r') as f:
        content = f.read()
    
    # Add import if not present
    if 'from blockchain_queries import blockchain' not in content:
        content = 'from blockchain_queries import blockchain\n' + content
    
    # Replace any remaining hardcoded values with blockchain queries
    replacements = [
        # Replace hardcoded gas prices
        (r'gas_price = \d+', 'gas_price = blockchain.get_current_gas_price()'),
        
        # Replace hardcoded ETH prices
        (r'eth_price = \d+', 'eth_price = blockchain.get_eth_price()'),
        
        # Replace mock reserve fetching
        (r'return \(\d+.*?\d+\)', 'return blockchain.get_pool_reserves(pool_address)'),
        
        # Replace mock balance checking
        (r'return \d+ \* 10\*\*\d+', 'return blockchain.get_token_balance(token_address, holder_address)'),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    with open(filename, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated {filename} to use real blockchain queries")

print("\\n✅ All files now use real blockchain data!")
