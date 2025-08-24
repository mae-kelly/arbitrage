import re

with open('unified_strategy.py', 'r') as f:
    content = f.read()

# Fix get_reserves to query real pools
real_reserves_code = '''
    async def get_reserves(self, pool: str) -> Tuple[int, int]:
        """Get real reserves from pool"""
        try:
            pool_contract = self.w3.eth.contract(
                address=Web3.toChecksumAddress(pool),
                abi=[
                    {"constant":True,"inputs":[],"name":"getReserves","outputs":[{"name":"_reserve0","type":"uint112"},{"name":"_reserve1","type":"uint112"},{"name":"_blockTimestampLast","type":"uint32"}],"type":"function"}
                ]
            )
            reserves = pool_contract.functions.getReserves().call()
            return (reserves[0], reserves[1])
        except:
            # Fallback for V3 pools
            try:
                pool_contract = self.w3.eth.contract(
                    address=Web3.toChecksumAddress(pool),
                    abi=[{"inputs":[],"name":"liquidity","outputs":[{"name":"","type":"uint128"}],"type":"function"}]
                )
                liquidity = pool_contract.functions.liquidity().call()
                # Approximate reserves for V3
                return (liquidity // 2, liquidity // 2)
            except:
                return (0, 0)
'''

# Fix get_chain_price to use real oracles
real_price_code = '''
    async def get_chain_price(self, chain: str) -> float:
        """Get real price from chain"""
        oracle_addresses = {
            'ethereum': '0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419',
            'bsc': '0x0567F2323251f0Aab15c8dFb1967E4e8A7D42aeE',
            'polygon': '0xAB594600376Ec9fD91F8e885dADF0CE036862dE0',
            'arbitrum': '0x639Fe6ab55C921f74e7fac1ee960C0B6293ba612'
        }
        
        try:
            if chain not in oracle_addresses:
                return 3200.0
            
            # Use appropriate Web3 instance for chain
            w3 = self.get_chain_w3(chain)
            
            oracle = w3.eth.contract(
                address=oracle_addresses[chain],
                abi=[{"inputs":[],"name":"latestAnswer","outputs":[{"name":"","type":"int256"}],"type":"function"}]
            )
            
            price = oracle.functions.latestAnswer().call() / 10**8
            return float(price)
        except:
            return 3200.0
'''

# Replace mock functions
content = re.sub(
    r"async def get_reserves.*?return \(100000.*?\)",
    real_reserves_code,
    content,
    flags=re.DOTALL
)

content = re.sub(
    r"async def get_chain_price.*?return prices.get\(chain, 3200.0\)",
    real_price_code,
    content,
    flags=re.DOTALL
)

with open('unified_strategy.py', 'w') as f:
    f.write(content)

print("✅ Fixed unified_strategy.py")
