#!/usr/bin/env python3
from blockchain_queries import blockchain
import asyncio

async def test_infrastructure():
    print("🚀 MEV Bot Infrastructure Test")
    print("=" * 50)
    
    # Test connection
    if blockchain.w3.is_connected():
        print(f"✅ Connected to Ethereum")
        print(f"   Block: {blockchain.w3.eth.block_number:,}")
        print(f"   Chain ID: {blockchain.w3.eth.chain_id}")
        
        # Get real data
        gas_price = blockchain.get_current_gas_price()
        eth_price = blockchain.get_eth_price()
        
        print(f"   Gas Price: {gas_price / 10**9:.2f} gwei")
        print(f"   ETH Price: ${eth_price:,.2f}" if eth_price else "   ETH Price: Unable to fetch")
        
        # Calculate real MEV scenario
        print("\n💰 Real MEV Calculation:")
        
        # Get a real pool
        weth_usdc_pool = '0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640'  # Uniswap V3
        liquidity = blockchain.get_v3_pool_liquidity(weth_usdc_pool)
        
        if liquidity > 0:
            print(f"   Pool Liquidity: {liquidity}")
            
            # Calculate sandwich for different trade sizes
            trade_sizes = [10 * 10**18, 50 * 10**18, 100 * 10**18]  # 10, 50, 100 ETH
            
            for size in trade_sizes:
                result = blockchain.calculate_sandwich_profit(weth_usdc_pool, size)
                if result['profitable']:
                    size_eth = size / 10**18
                    profit_eth = result['net_profit'] / 10**18
                    profit_usd = profit_eth * eth_price if eth_price else 0
                    
                    print(f"\n   {size_eth:.0f} ETH trade:")
                    print(f"     Net Profit: {profit_eth:.6f} ETH (${profit_usd:.2f})")
        
        # Check real pending transactions
        print("\n📊 Current Mempool:")
        pending = blockchain.get_pending_transactions(10)
        large_txs = [tx for tx in pending if tx.get('value', 0) > 10 * 10**18]
        
        print(f"   Pending transactions checked: {len(pending)}")
        print(f"   Large transactions (>10 ETH): {len(large_txs)}")
        
        # Real arbitrage check
        print("\n🔄 Arbitrage Opportunities:")
        
        # Check between real pools
        uni_v2_pool = '0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'  # WETH/USDC V2
        sushi_pool = '0x397FF1542f962076d0BFE58eA045FfA2d347ACa0'   # WETH/USDC Sushi
        
        arb = blockchain.find_arbitrage_opportunity(
            '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
            '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',  # USDC
            uni_v2_pool,
            sushi_pool
        )
        
        if arb['profitable']:
            print(f"   ✅ Arbitrage found!")
            print(f"   Price difference: {arb['price_diff']*100:.3f}%")
            print(f"   Net profit: {arb['net_profit'] / 10**18:.6f} ETH")
        else:
            print("   No profitable arbitrage currently")
    else:
        print("❌ Not connected to Ethereum")

if __name__ == "__main__":
    asyncio.run(test_infrastructure())
