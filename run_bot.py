#!/usr/bin/env python3
import asyncio
import os
import sys
from dotenv import load_dotenv
from web3 import Web3

# Load environment variables
load_dotenv()

# Add paths
sys.path.append('bot')
sys.path.append('core')

async def main():
    print("🚀 Starting MEV Bot...")
    
    # Check configuration
    if not os.getenv('ALCHEMY_KEY') or os.getenv('ALCHEMY_KEY') == 'your_alchemy_key_here':
        print("❌ Please set your ALCHEMY_KEY in .env file")
        print("   Get one at: https://www.alchemy.com/")
        return
    
    if not os.getenv('PRIVATE_KEY') or os.getenv('PRIVATE_KEY').startswith('0x000'):
        print("❌ Please set your PRIVATE_KEY in .env file")
        print("   Generate one with: python3 -c 'from eth_account import Account; print(Account.create().key.hex())'")
        return
    
    # Test connection
    w3 = Web3(Web3.HTTPProvider(os.getenv('ETH_RPC_URL') + os.getenv('ALCHEMY_KEY')))
    if w3.is_connected():
        print(f"✅ Connected to Ethereum")
        print(f"   Latest block: {w3.eth.block_number:,}")
        print(f"   Gas price: {w3.eth.gas_price / 10**9:.2f} gwei")
    else:
        print("❌ Failed to connect to Ethereum")
        return
    
    # Import and run engine
    try:
        from engine import MEVEngine
        engine = MEVEngine()
        await engine.run()
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Run: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
