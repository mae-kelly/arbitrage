#!/usr/bin/env python3

# Fix check_flash_loans.py
check_flash_loans_content = '''#!/usr/bin/env python3
from blockchain_queries import blockchain
import asyncio

async def check_real_flash_loans():
    """Check real flash loan availability"""
    
    print("💰 Flash Loan Availability (Real-time)")
    print("=" * 40)
    
    tokens = {
        'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
        'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
        'DAI': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
        'WETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
    }
    
    eth_price = blockchain.get_eth_price()
    
    total = 0
    for token_name, token_address in tokens.items():
        # Check Aave
        aave_available = blockchain.get_flash_loan_availability('aave', token_address)
        
        # Convert to readable format
        if token_name == 'WETH':
            decimals = 18
            usd_value = (aave_available / 10**decimals) * eth_price if eth_price else 0
        elif token_name in ['USDC', 'USDT']:
            decimals = 6
            usd_value = aave_available / 10**decimals
        else:  # DAI
            decimals = 18
            usd_value = aave_available / 10**decimals
        
        print(f"Aave {token_name}: ${usd_value:,.0f}")
        total += usd_value
        
        # Check Balancer
        balancer_available = blockchain.get_flash_loan_availability('balancer', token_address)
        if token_name in ['USDC', 'USDT']:
            balancer_usd = balancer_available / 10**6
            print(f"Balancer {token_name}: ${balancer_usd:,.0f}")
            total += balancer_usd
    
    print(f"\\nTotal Available: ${total:,.0f}")
    
    # Get current fees
    print("\\nCurrent Fees:")
    print("  Aave: 0.09%")
    print("  Balancer: 0%")
    print("  Uniswap V3: 0.05%")
    
    # Calculate costs
    gas_price = blockchain.get_current_gas_price()
    print(f"\\nCurrent Gas Price: {gas_price / 10**9:.2f} gwei")
    flash_loan_gas = 400000
    cost_eth = (flash_loan_gas * gas_price) / 10**18
    cost_usd = cost_eth * eth_price if eth_price else 0
    print(f"Flash Loan Gas Cost: ${cost_usd:.2f}")

if __name__ == "__main__":
    asyncio.run(check_real_flash_loans())
'''

with open('check_flash_loans.py', 'w') as f:
    f.write(check_flash_loans_content)

print("✅ Fixed check_flash_loans.py")

# Fix test_bot.py
test_bot_content = '''#!/usr/bin/env python3
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
        print("\\n💰 Real MEV Calculation:")
        
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
                    
                    print(f"\\n   {size_eth:.0f} ETH trade:")
                    print(f"     Net Profit: {profit_eth:.6f} ETH (${profit_usd:.2f})")
        
        # Check real pending transactions
        print("\\n📊 Current Mempool:")
        pending = blockchain.get_pending_transactions(10)
        large_txs = [tx for tx in pending if tx.get('value', 0) > 10 * 10**18]
        
        print(f"   Pending transactions checked: {len(pending)}")
        print(f"   Large transactions (>10 ETH): {len(large_txs)}")
        
        # Real arbitrage check
        print("\\n🔄 Arbitrage Opportunities:")
        
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
'''

with open('test_bot.py', 'w') as f:
    f.write(test_bot_content)

print("✅ Fixed test_bot.py")

# Fix live scanner
live_scanner_content = '''#!/usr/bin/env python3
from blockchain_queries import blockchain
import asyncio
from datetime import datetime

async def scan_live():
    print("🔍 Live MEV Scanner")
    print("=" * 50)
    
    while True:
        try:
            block = blockchain.w3.eth.get_block('latest', full_transactions=True)
            print(f"\\nBlock {block['number']:,} at {datetime.now().strftime('%H:%M:%S')}")
            
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
'''

with open('check_mev_live.py', 'w') as f:
    f.write(live_scanner_content)

print("✅ Fixed check_mev_live.py")
