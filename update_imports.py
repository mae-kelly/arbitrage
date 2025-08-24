#!/usr/bin/env python3
"""Update all Python files to use dynamic configuration"""

import os
import re

files_to_update = [
    'flashloan_aggregator.py',
    'mev_predictor.py', 
    'liquidation_predictor_ml.py',
    'oracle_manipulation.py',
    'cross_chain_sync.py',
    'engine.py',
    'unified_strategy.py',
    'advanced_sandwich.py',
    'private_order_flow.py'
]

import_statement = """from config_loader import config
from contract_registry import ContractRegistry
"""

for filename in files_to_update:
    if not os.path.exists(filename):
        continue
    
    with open(filename, 'r') as f:
        content = f.read()
    
    # Add imports if not present
    if 'from config_loader import config' not in content:
        content = import_statement + content
    
    # Replace hardcoded addresses with config references
    content = re.sub(
        r"'0x[a-fA-F0-9]{40}'",
        lambda m: f"config.config['contracts'].get('contract_name', {m.group()})",
        content
    )
    
    with open(filename, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated {filename}")

print("\n✅ All files updated to use dynamic configuration")
