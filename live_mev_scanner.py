#!/usr/bin/env python3
# live_mev_scanner.py - Real-time MEV opportunity scanner

from web3 import Web3
import asyncio
import time
from datetime import datetime

class LiveMEVScanner:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider('https://eth.llamarpc.com'))
        self.dex_routers = {
            '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D': 'Uniswap V2',
            '0xE592427A0AEce92De3Edee1F18E0157C05861564': 'Uniswap V3',
            '0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F': 'SushiSwap',
            '0x1111111254EEB25477B68fb85Ed929f73A960582': '1inch'
        }
        self.opportunities_found = []
        
    def analyze_transaction(self, tx):
        """Analyze a transaction for MEV opportunities"""
        # Check if it's a DEX transaction
        if tx.get('to') in self.dex_routers:
            value_eth = tx.get('value', 0) / 10**18
            gas_price = tx.get('gasPrice', 0) / 10**9
            
            if value_eth > 0.1:  # Significant transaction
                return {
                    'type': 'sandwich',
                    'dex': self.dex_routers[tx['to']],
                    'value_eth': value_eth,
                    'gas_price_gwei': gas_price,
                    'tx_hash': tx['hash'].hex(),
                    'from': tx['from'],
                    'profit_estimate': value_eth * 0.003  # 0.3% estimate
                }
        
        # Check for liquidations (high gas price, specific contracts)
        if tx.get('gasPrice', 0) / 10**9 > 50:  # High priority transaction
            return {
                'type': 'potential_liquidation',
                'gas_price_gwei': tx.get('gasPrice', 0) / 10**9,
                'tx_hash': tx['hash'].hex(),
                'value_eth': tx.get('value', 0) / 10**18
            }
        
        return None
    
    async def scan_current_block(self):
        """Scan the current block for opportunities"""
        try:
            block = self.w3.eth.get_block('latest', full_transactions=True)
            print(f"\n🔍 Scanning Block: {block['number']:,}")
            print(f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}")
            print(f"📊 Transactions: {len(block['transactions'])}")
            print(f"⛽ Base Fee: {block.get('baseFeePerGas', 0) / 10**9:.2f} gwei")
            
            opportunities = []
            
            for tx in block['transactions']:
                opp = self.analyze_transaction(tx)
                if opp:
                    opportunities.append(opp)
            
            if opportunities:
                print(f"\n💰 Found {len(opportunities)} MEV Opportunities:")
                
                for i, opp in enumerate(opportunities[:10], 1):  # Show top 10
                    if opp['type'] == 'sandwich':
                        print(f"\n  {i}. SANDWICH OPPORTUNITY")
                        print(f"     DEX: {opp['dex']}")
                        print(f"     Value: {opp['value_eth']:.4f} ETH")
                        print(f"     Gas: {opp['gas_price_gwei']:.2f} gwei")
                        print(f"     Est. Profit: ${opp['profit_estimate'] * 2500:.2f}")
                        print(f"     TX: {opp['tx_hash'][:10]}...")
                    
                    elif opp['type'] == 'potential_liquidation':
                        print(f"\n  {i}. LIQUIDATION SIGNAL")
                        print(f"     High Gas: {opp['gas_price_gwei']:.2f} gwei")
                        print(f"     TX: {opp['tx_hash'][:10]}...")
                
                # Calculate total potential
                total_profit = sum(o.get('profit_estimate', 0) for o in opportunities if o['type'] == 'sandwich')
                print(f"\n📈 Total Potential Profit: {total_profit:.4f} ETH (${total_profit * 2500:.2f})")
            else:
                print("❌ No obvious MEV opportunities in this block")
                
            return opportunities
            
        except Exception as e:
            print(f"Error: {e}")
            return []
    
    async def monitor_mempool(self):
        """Monitor mempool for pending transactions"""
        print("\n🎯 Monitoring Mempool (Pending Transactions)...")
        print("Note: Public RPCs have limited mempool access")
        
        try:
            # Try to get pending transactions (may be limited on public RPC)
            pending = self.w3.eth.get_block('pending', full_transactions=True)
            if pending and pending.get('transactions'):
                print(f"Found {len(pending['transactions'])} pending transactions")
                
                for tx in pending['transactions'][:5]:
                    if tx.get('to') in self.dex_routers:
                        print(f"  ⚡ Pending DEX trade on {self.dex_routers[tx['to']]}")
                        print(f"     Value: {tx.get('value', 0) / 10**18:.4f} ETH")
            else:
                print("  ⚠️ Mempool access limited on public RPC")
                print("  💡 For real mempool access, you need:")
                print("     - Paid RPC service (Alchemy, Infura)")
                print("     - Or direct node connection")
                
        except Exception as e:
            print(f"  ⚠️ Cannot access mempool: {e}")
    
    async def run_continuous_scan(self):
        """Run continuous scanning"""
        print("🚀 Starting LIVE MEV Scanner")
        print("=" * 50)
        
        while True:
            await self.scan_current_block()
            await self.monitor_mempool()
            
            print("\n⏳ Waiting for next block (~12 seconds)...")
            await asyncio.sleep(12)

async def main():
    scanner = LiveMEVScanner()
    
    # Check connection
    if scanner.w3.is_connected():
        print(f"✅ Connected to Ethereum Mainnet")
        print(f"📦 Current Block: {scanner.w3.eth.block_number:,}")
        print(f"⛽ Gas Price: {scanner.w3.eth.gas_price / 10**9:.2f} gwei")
        print("")
        
        # Run scanner
        await scanner.run_continuous_scan()
    else:
        print("❌ Failed to connect to Ethereum")

if __name__ == "__main__":
    print("=" * 50)
    print("        LIVE MEV OPPORTUNITY SCANNER")
    print("=" * 50)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Scanner stopped")