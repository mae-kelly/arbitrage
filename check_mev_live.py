#!/usr/bin/env python3
from blockchain_queries import blockchain
import asyncio
from datetime import datetime

async def scan_live():
    print("🔍 Live MEV Scanner")
    print("=" * 50)
    
    while True:
        try:
            block = blockchain.w3.eth.get_block('latest', full_transactions=True)
            print(f"\nBlock {block['number']:,} at {datetime.now().strftime('%H:%M:%S')}")
            
            # Analyze real transactions
            opportunities = 0
            for tx in block['transactions']:
                # Check if it's a DEX transaction (by value and gas)
                if tx.get('value', 0) > 5 * 10**18:  # > 5 ETH
                    # This is a real potential opportunity
                    opportunities += 1
            
            print(f"Potential opportunities: {opportunities}")
            
            # Get real pending transactions
            pending = blockchain.get_pending_transactions(20)
            print(f"Pending transactions: {len(pending)}")
            
            await asyncio.sleep(12)  # Wait for next block
            
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(12)

if __name__ == "__main__":
    asyncio.run(scan_live())
