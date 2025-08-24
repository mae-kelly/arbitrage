#!/usr/bin/env python3
"""
Dynamic contract registry that fetches addresses from on-chain or APIs
"""

from web3 import Web3
import json
import aiohttp
import asyncio

class ContractRegistry:
    def __init__(self, w3: Web3):
        self.w3 = w3
        self.contracts = {}
        self.last_update = 0
        
    async def update_contracts(self):
        """Update contract addresses from various sources"""
        
        # 1. Try to load from local cache
        if self.load_from_cache():
            return
        
        # 2. Fetch from Etherscan API
        await self.fetch_from_etherscan()
        
        # 3. Fetch from DeFiLlama
        await self.fetch_from_defillama()
        
        # 4. Query on-chain registries
        await self.query_onchain_registries()
        
        # Save to cache
        self.save_to_cache()
    
    def load_from_cache(self) -> bool:
        """Load contracts from local cache"""
        try:
            with open('contracts_cache.json', 'r') as f:
                data = json.load(f)
                
                # Check if cache is recent (less than 1 day old)
                import time
                if time.time() - data.get('timestamp', 0) < 86400:
                    self.contracts = data['contracts']
                    return True
        except:
            pass
        
        return False
    
    async def fetch_from_etherscan(self):
        """Fetch verified contracts from Etherscan"""
        api_key = os.getenv('ETHERSCAN_KEY')
        if not api_key:
            return
        
        # Known contract names to search for
        contract_names = [
            'Uniswap V2: Router 2',
            'Uniswap V3: Router',
            'SushiSwap: Router',
            'Aave V3: Pool',
            'Compound III',
            'Balancer: Vault'
        ]
        
        async with aiohttp.ClientSession() as session:
            for name in contract_names:
                url = f"https://api.etherscan.io/api?module=contract&action=searchcontract&contractname={name}&apikey={api_key}"
                
                try:
                    async with session.get(url) as response:
                        data = await response.json()
                        if data['status'] == '1' and data['result']:
                            # Parse and store contract addresses
                            for contract in data['result']:
                                self.contracts[contract['ContractName']] = contract['Address']
                except:
                    continue
    
    async def fetch_from_defillama(self):
        """Fetch protocol addresses from DeFiLlama"""
        async with aiohttp.ClientSession() as session:
            url = "https://api.llama.fi/protocols"
            
            try:
                async with session.get(url) as response:
                    protocols = await response.json()
                    
                    # Extract addresses for major protocols
                    for protocol in protocols:
                        if protocol.get('address') and protocol.get('name'):
                            self.contracts[protocol['name']] = protocol['address']
            except:
                pass
    
    async def query_onchain_registries(self):
        """Query on-chain contract registries"""
        
        # ENS Registry
        ens_registry = "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e"
        
        # Uniswap V3 Factory
        uni_v3_factory = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
        
        try:
            # Query factory for pool addresses
            factory = self.w3.eth.contract(
                address=uni_v3_factory,
                abi=[{
                    "inputs": [
                        {"name": "tokenA", "type": "address"},
                        {"name": "tokenB", "type": "address"},
                        {"name": "fee", "type": "uint24"}
                    ],
                    "name": "getPool",
                    "outputs": [{"name": "pool", "type": "address"}],
                    "type": "function"
                }]
            )
            
            # Get major pools
            weth = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
            usdc = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
            
            for fee in [500, 3000, 10000]:
                pool = factory.functions.getPool(weth, usdc, fee).call()
                if pool != "0x0000000000000000000000000000000000000000":
                    self.contracts[f"UniV3_WETH_USDC_{fee}"] = pool
                    
        except:
            pass
    
    def save_to_cache(self):
        """Save contracts to cache file"""
        import time
        
        cache_data = {
            'timestamp': time.time(),
            'contracts': self.contracts
        }
        
        with open('contracts_cache.json', 'w') as f:
            json.dump(cache_data, f, indent=2)
    
    def get_contract(self, name: str) -> str:
        """Get contract address by name"""
        return self.contracts.get(name, None)
    
    def get_all_contracts(self) -> Dict:
        """Get all contract addresses"""
        return self.contracts

# Usage
async def main():
    w3 = Web3(Web3.HTTPProvider('https://eth.llamarpc.com'))
    registry = ContractRegistry(w3)
    await registry.update_contracts()
    print(f"Loaded {len(registry.contracts)} contracts")

if __name__ == "__main__":
    asyncio.run(main())
