# Patch for flashloan_aggregator.py
import json

def get_real_limits_code():
    return '''
    async def get_real_protocol_limits(self):
        """Get real-time liquidity from protocols"""
        limits = {}
        
        # Aave V3 - Query actual reserves
        for token_symbol, token_address in self.token_addresses.items():
            try:
                aave_pool = self.w3.eth.contract(
                    address=self.protocols['aave_v3']['address'],
                    abi=[{"inputs":[{"name":"asset","type":"address"}],"name":"getReserveData","outputs":[{"components":[{"name":"configuration","type":"uint256"},{"name":"liquidityIndex","type":"uint128"},{"name":"currentLiquidityRate","type":"uint128"},{"name":"variableBorrowIndex","type":"uint128"},{"name":"currentVariableBorrowRate","type":"uint128"},{"name":"currentStableBorrowRate","type":"uint128"},{"name":"lastUpdateTimestamp","type":"uint40"},{"name":"id","type":"uint16"},{"name":"aTokenAddress","type":"address"},{"name":"stableDebtTokenAddress","type":"address"},{"name":"variableDebtTokenAddress","type":"address"},{"name":"interestRateStrategyAddress","type":"address"},{"name":"accruedToTreasury","type":"uint128"},{"name":"unbacked","type":"uint128"},{"name":"isolationModeTotalDebt","type":"uint128"}],"name":"","type":"tuple"}],"stateMutability":"view","type":"function"}]
                )
                
                # Get aToken balance for available liquidity
                reserve_data = aave_pool.functions.getReserveData(token_address).call()
                atoken_address = reserve_data[8]
                
                token_contract = self.w3.eth.contract(
                    address=token_address,
                    abi=[{"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}]
                )
                
                available = token_contract.functions.balanceOf(atoken_address).call()
                
                if 'aave_v3' not in limits:
                    limits['aave_v3'] = {}
                limits['aave_v3'][token_symbol] = available
                
            except Exception as e:
                print(f"Error getting {token_symbol} limit: {e}")
                limits['aave_v3'][token_symbol] = 0
        
        # Balancer - Query vault balance
        for token_symbol, token_address in self.token_addresses.items():
            try:
                token_contract = self.w3.eth.contract(
                    address=token_address,
                    abi=[{"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}]
                )
                
                vault_balance = token_contract.functions.balanceOf(self.protocols['balancer']['address']).call()
                
                if 'balancer' not in limits:
                    limits['balancer'] = {}
                limits['balancer'][token_symbol] = vault_balance
                
            except:
                limits['balancer'][token_symbol] = 0
        
        return limits
    
    def __init__(self, w3):
        self.w3 = w3
        # Update protocol list with real values
        self.update_protocol_limits()
    
    async def update_protocol_limits(self):
        """Update limits with real-time data"""
        real_limits = await self.get_real_protocol_limits()
        for protocol_name, token_limits in real_limits.items():
            if protocol_name in self.protocols:
                self.protocols[protocol_name]['limits'] = token_limits
'''

with open('flashloan_aggregator.py', 'r') as f:
    content = f.read()

# Replace the hardcoded limits
import re
content = re.sub(
    r"'limits': \{[^}]+\}",
    "'limits': {}  # Will be populated dynamically",
    content
)

# Add the real limits function
content = content.replace(
    "def __init__(self, w3):",
    get_real_limits_code() + "\n    def __init_old__(self, w3):"
)

with open('flashloan_aggregator.py', 'w') as f:
    f.write(content)

print("✅ Fixed flashloan_aggregator.py")
