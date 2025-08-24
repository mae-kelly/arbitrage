#!/bin/bash

# Fix the calculate_profit_from_receipt function
cat > fix_engine_profit.py << 'PYTHON'
def get_real_profit_calculation():
    return '''
    def calculate_profit_from_receipt(self, receipt):
        """Calculate real profit from transaction receipt"""
        try:
            # Parse logs for profit events
            profit = 0
            
            # Look for Transfer events to our address
            transfer_topic = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
            
            for log in receipt['logs']:
                if log['topics'][0].hex() == transfer_topic:
                    # Check if transfer is to our address
                    if len(log['topics']) >= 3:
                        to_address = '0x' + log['topics'][2].hex()[-40:]
                        if to_address.lower() == self.account.address.lower():
                            # Decode amount (uint256)
                            amount = int(log['data'].hex(), 16)
                            
                            # Determine token from address
                            token_address = log['address']
                            
                            # Convert to USD value
                            if token_address.lower() == '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48':  # USDC
                                profit += amount
                            elif token_address.lower() == '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2':  # WETH
                                eth_price = self.get_eth_price()
                                profit += (amount / 10**18) * eth_price * 10**6
                            elif token_address.lower() == '0xdac17f958d2ee523a2206206994597c13d831ec7':  # USDT
                                profit += amount
            
            # Subtract gas costs
            gas_cost = receipt['gasUsed'] * receipt['effectiveGasPrice']
            eth_price = self.get_eth_price()
            gas_cost_usd = (gas_cost / 10**18) * eth_price * 10**6
            
            net_profit = profit - gas_cost_usd
            
            return max(0, net_profit)
            
        except Exception as e:
            print(f"Error calculating profit: {e}")
            return 0
    
    def get_eth_price(self):
        """Get current ETH price from Chainlink oracle"""
        try:
            oracle = self.w3_eth.eth.contract(
                address='0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419',
                abi=[{"inputs":[],"name":"latestAnswer","outputs":[{"name":"","type":"int256"}],"type":"function"}]
            )
            price = oracle.functions.latestAnswer().call() / 10**8
            return price
        except:
            return 3200  # Fallback price
    '''

with open('engine.py', 'r') as f:
    content = f.read()

# Replace the mock function
content = content.replace(
    "def calculate_profit_from_receipt(self, receipt):\n        return 1000000 * 10**6",
    get_real_profit_calculation()
)

with open('engine.py', 'w') as f:
    f.write(content)

print("✅ Fixed engine.py profit calculation")
PYTHON

python3 fix_engine_profit.py
echo "✅ Fixed engine.py"
