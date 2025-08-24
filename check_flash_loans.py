#!/usr/bin/env python3
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
    
    print(f"\nTotal Available: ${total:,.0f}")
    
    # Get current fees
    print("\nCurrent Fees:")
    print("  Aave: 0.09%")
    print("  Balancer: 0%")
    print("  Uniswap V3: 0.05%")
    
    # Calculate costs
    gas_price = blockchain.get_current_gas_price()
    print(f"\nCurrent Gas Price: {gas_price / 10**9:.2f} gwei")
    flash_loan_gas = 400000
    cost_eth = (flash_loan_gas * gas_price) / 10**18
    cost_usd = cost_eth * eth_price if eth_price else 0
    print(f"Flash Loan Gas Cost: ${cost_usd:.2f}")

if __name__ == "__main__":
    asyncio.run(check_real_flash_loans())
