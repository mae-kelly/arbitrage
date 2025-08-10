import sys
import re

# Read the file
with open('src/lib.rs', 'r') as f:
    content = f.read()

# Fix 1: Change symbol references from &str to String
content = re.sub(r'base_prices\.get\(symbol\)', r'base_prices.get(&symbol.to_string())', content)
content = re.sub(r'exchange_feeds\.get\(symbol\)', r'exchange_feeds.get(&symbol.to_string())', content)

# Fix 2: Add rand imports
if 'use rand' not in content:
    # Add after other use statements
    content = re.sub(r'(use tracing[^;]+;)', r'\1\nuse rand::Rng;', content)

# Fix 3: Fix symbol.clone() type mismatch
content = re.sub(r'symbol: symbol\.clone\(\)', r'symbol: symbol.to_string()', content)

# Write the fixed content
with open('src/lib_fixed.rs', 'w') as f:
    f.write(content)
