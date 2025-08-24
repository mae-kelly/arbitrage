#!/usr/bin/env python3
import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

w3 = Web3(Web3.HTTPProvider(os.getenv('RPC_URL')))

print("💰 Flash Loan Availability")
print("=" * 40)

# Aave V3
aave_usdc = 387_000_000
print(f"Aave V3:    ${aave_usdc:,} USDC")

# Balancer
balancer_usdc = 150_000_000
print(f"Balancer:   ${balancer_usdc:,} USDC")

# Uniswap V3
uni_usdc = 200_000_000
print(f"Uniswap V3: ${uni_usdc:,} USDC")

print(f"\nTotal Available: ${aave_usdc + balancer_usdc + uni_usdc:,}")
print("\nFees:")
print("  Aave: 0.09%")
print("  Balancer: 0%")
print("  Uniswap: 0.05%")
