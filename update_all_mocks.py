#!/usr/bin/env python3
import json
import os
import re

def update_file_with_config(filename, config):
    """Update a file to use real config values"""
    if not os.path.exists(filename):
        print(f"⚠️  {filename} not found")
        return
    
    with open(filename, 'r') as f:
        content = f.read()
    
    # Replace hardcoded addresses with config references
    for category, addresses in config.items():
        if isinstance(addresses, dict):
            for name, address in addresses.items():
                # Replace hardcoded addresses
                content = re.sub(
                    f"['\"]0x[a-fA-F0-9]{{40}}['\"].*# *{name}",
                    f"config['{category}']['{name}']  # {name}",
                    content,
                    flags=re.IGNORECASE
                )
    
    with open(filename, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated {filename}")

# Load config
with open('real_config.json', 'r') as f:
    config = json.load(f)

# Update all Python files
python_files = [
    'flashloan_aggregator.py',
    'mev_predictor.py',
    'liquidation_predictor_ml.py',
    'oracle_manipulation.py',
    'cross_chain_sync.py',
    'engine.py',
    'unified_strategy.py'
]

for file in python_files:
    update_file_with_config(file, config)

print("\n✅ All files updated with real contract addresses")
