"""Multi-chain DEX manager for cross-chain arbitrage"""
import asyncio
from typing import Dict, List, Optional, Tuple
from web3 import Web3
from web3.middleware import geth_poa_middleware
import json
from decimal import Decimal
from loguru import logger
import redis.asyncio as redis

class MultiChainDEXManager:
    def __init__(self):
        self.w3_connections = {}
        self.dex_contracts = {}
        self.gas_prices = {}
        self.redis_client = None
        
        self.blockchain_configs = {
            "ethereum": {
                "chain_id": 1,
                "rpc_urls": [
                    "https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY",
                    "https://mainnet.infura.io/v3/YOUR_KEY",
                    "https://rpc.ankr.com/eth",
                    "https://cloudflare-eth.com"
                ],
                "dexs": {
                    "uniswap_v2": {
                        "factory": "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
                        "router": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
                    },
                    "uniswap_v3": {
                        "factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
                        "router": "0xE592427A0AEce92De3Edee1F18E0157C05861564"
                    },
                    "sushiswap": {
                        "factory": "0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac",
                        "router": "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F"
                    }
                },
                "tokens": {
                    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
                    "USDC": "0xA0b86a33E6441b8435b662d50cc6fc73d55BAed"
                }
            },
            "bsc": {
                "chain_id": 56,
                "rpc_urls": [
                    "https://bsc-dataseed1.binance.org",
                    "https://bsc-dataseed2.binance.org",
                    "https://bsc-dataseed3.binance.org"
                ],
                "dexs": {
                    "pancakeswap": {
                        "factory": "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73",
                        "router": "0x10ED43C718714eb63d5aA57B78B54704E256024E"
                    },
                    "biswap": {
                        "factory": "0x858E3312ed3A876947EA49d572A7C42DE08af7EE",
                        "router": "0x3a6d8cA21D1CF76F653A67577FA0D27453350dD8"
                    }
                },
                "tokens": {
                    "WBNB": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
                    "USDT": "0x55d398326f99059fF775485246999027B3197955",
                    "USDC": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"
                }
            },
            "polygon": {
                "chain_id": 137,
                "rpc_urls": [
                    "https://polygon-rpc.com",
                    "https://rpc-mainnet.matic.network",
                    "https://matic-mainnet.chainstacklabs.com"
                ],
                "dexs": {
                    "quickswap": {
                        "factory": "0x5757371414417b8C6CAad45bAeF941aBc7d3Ab32",
                        "router": "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff"
                    },
                    "sushiswap": {
                        "factory": "0xc35DADB65012eC5796536bD9864eD8773aBc74C4",
                        "router": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506"
                    }
                },
                "tokens": {
                    "WMATIC": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
                    "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
                    "USDC": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
                }
            },
            "arbitrum": {
                "chain_id": 42161,
                "rpc_urls": [
                    "https://arb1.arbitrum.io/rpc",
                    "https://arbitrum-mainnet.infura.io/v3/YOUR_KEY"
                ],
                "dexs": {
                    "uniswap_v3": {
                        "factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
                        "router": "0xE592427A0AEce92De3Edee1F18E0157C05861564"
                    },
                    "sushiswap": {
                        "factory": "0xc35DADB65012eC5796536bD9864eD8773aBc74C4",
                        "router": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506"
                    }
                },
                "tokens": {
                    "WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
                    "USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
                    "USDC": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8"
                }
            }
        }
    
    async def initialize(self):
        """Initialize all blockchain connections"""
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        for chain_id, config in self.blockchain_configs.items():
            await self._connect_to_chain(chain_id, config)
        
        # Start gas price monitoring
        asyncio.create_task(self.monitor_gas_prices())
    
    async def _connect_to_chain(self, chain_id: str, config: Dict):
        """Connect to blockchain with fallback RPC endpoints"""
        for rpc_url in config['rpc_urls']:
            try:
                w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 10}))
                
                # Add PoA middleware for BSC and Polygon
                if chain_id in ['bsc', 'polygon']:
                    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                
                if w3.is_connected():
                    self.w3_connections[chain_id] = w3
                    logger.success(f"Connected to {chain_id} via {rpc_url}")
                    
                    # Load DEX contracts
                    await self._load_dex_contracts(chain_id, config['dexs'])
                    break
                    
            except Exception as e:
                logger.warning(f"Failed to connect to {chain_id} via {rpc_url}: {e}")
                continue
        else:
            logger.error(f"Failed to connect to {chain_id} - all RPC endpoints failed")
    
    async def _load_dex_contracts(self, chain_id: str, dexs: Dict):
        """Load DEX smart contracts for the chain"""
        # Uniswap V2 Factory ABI (minimal)
        factory_abi = [
            {
                "inputs": [{"type": "address"}, {"type": "address"}],
                "name": "getPair",
                "outputs": [{"type": "address"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        # Uniswap V2 Pair ABI (minimal)
        pair_abi = [
            {
                "inputs": [],
                "name": "getReserves",
                "outputs": [{"type": "uint112"}, {"type": "uint112"}, {"type": "uint32"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "token0",
                "outputs": [{"type": "address"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "token1",
                "outputs": [{"type": "address"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        w3 = self.w3_connections[chain_id]
        self.dex_contracts[chain_id] = {}
        
        for dex_name, addresses in dexs.items():
            try:
                factory_contract = w3.eth.contract(
                    address=addresses['factory'],
                    abi=factory_abi
                )
                
                self.dex_contracts[chain_id][dex_name] = {
                    'factory': factory_contract,
                    'pair_abi': pair_abi
                }
                
                logger.success(f"Loaded {dex_name} contracts on {chain_id}")
                
            except Exception as e:
                logger.error(f"Failed to load {dex_name} on {chain_id}: {e}")
    
    async def get_token_price(self, chain_id: str, dex_name: str, token0: str, token1: str, amount_in: int = 10**18) -> Optional[Decimal]:
        """Get token price from DEX"""
        try:
            if chain_id not in self.dex_contracts or dex_name not in self.dex_contracts[chain_id]:
                return None
            
            factory = self.dex_contracts[chain_id][dex_name]['factory']
            pair_abi = self.dex_contracts[chain_id][dex_name]['pair_abi']
            w3 = self.w3_connections[chain_id]
            
            # Get pair address
            pair_address = factory.functions.getPair(token0, token1).call()
            if pair_address == '0x0000000000000000000000000000000000000000':
                return None
            
            # Get pair contract
            pair_contract = w3.eth.contract(address=pair_address, abi=pair_abi)
            
            # Get reserves
            reserves = pair_contract.functions.getReserves().call()
            token0_addr = pair_contract.functions.token0().call()
            
            # Calculate price based on reserves
            if token0_addr.lower() == token0.lower():
                reserve_in = reserves[0]
                reserve_out = reserves[1]
            else:
                reserve_in = reserves[1]
                reserve_out = reserves[0]
            
            if reserve_in == 0 or reserve_out == 0:
                return None
            
            # Uniswap V2 formula: amount_out = amount_in * 997 * reserve_out / (reserve_in * 1000 + amount_in * 997)
            amount_in_with_fee = amount_in * 997
            numerator = amount_in_with_fee * reserve_out
            denominator = reserve_in * 1000 + amount_in_with_fee
            amount_out = numerator // denominator
            
            return Decimal(amount_out) / Decimal(amount_in)
            
        except Exception as e:
            logger.error(f"Error getting price for {token0}/{token1} on {dex_name}: {e}")
            return None
    
    async def monitor_gas_prices(self):
        """Monitor gas prices across all chains"""
        while True:
            for chain_id, w3 in self.w3_connections.items():
                try:
                    gas_price = w3.eth.gas_price
                    self.gas_prices[chain_id] = gas_price
                    
                    # Store in Redis for analysis
                    await self.redis_client.zadd(
                        f"gas_price:{chain_id}",
                        {str(asyncio.get_event_loop().time()): gas_price}
                    )
                    
                    logger.debug(f"Gas price {chain_id}: {gas_price / 10**9:.2f} gwei")
                    
                except Exception as e:
                    logger.error(f"Failed to get gas price for {chain_id}: {e}")
            
            await asyncio.sleep(30)
    
    async def estimate_cross_chain_profit(self, token_symbol: str, amount: Decimal) -> List[Dict]:
        """Estimate profit from cross-chain arbitrage"""
        opportunities = []
        
        # Get token addresses for each chain
        token_addresses = {}
        for chain_id, config in self.blockchain_configs.items():
            if token_symbol in config['tokens']:
                token_addresses[chain_id] = config['tokens'][token_symbol]
        
        if len(token_addresses) < 2:
            return opportunities
        
        # Get prices on each chain
        prices = {}
        for chain_id, token_address in token_addresses.items():
            if chain_id in self.dex_contracts:
                for dex_name in self.dex_contracts[chain_id]:
                    # Get price against USDT/USDC
                    usdt_address = self.blockchain_configs[chain_id]['tokens'].get('USDT')
                    if usdt_address:
                        price = await self.get_token_price(chain_id, dex_name, token_address, usdt_address)
                        if price:
                            prices[f"{chain_id}_{dex_name}"] = {
                                'price': price,
                                'chain': chain_id,
                                'dex': dex_name,
                                'gas_price': self.gas_prices.get(chain_id, 0)
                            }
        
        # Find arbitrage opportunities
        price_keys = list(prices.keys())
        for i in range(len(price_keys)):
            for j in range(i + 1, len(price_keys)):
                buy_venue = price_keys[i]
                sell_venue = price_keys[j]
                
                buy_price = prices[buy_venue]['price']
                sell_price = prices[sell_venue]['price']
                
                if sell_price > buy_price:
                    profit_pct = (sell_price - buy_price) / buy_price
                    
                    # Estimate costs (simplified)
                    buy_gas_cost = prices[buy_venue]['gas_price'] * 150000 / 10**18  # Estimate
                    sell_gas_cost = prices[sell_venue]['gas_price'] * 150000 / 10**18
                    bridge_cost = Decimal('0.01')  # Simplified bridge cost
                    
                    total_costs = buy_gas_cost + sell_gas_cost + bridge_cost
                    net_profit = (amount * profit_pct) - total_costs
                    
                    if net_profit > 0:
                        opportunities.append({
                            'token': token_symbol,
                            'buy_venue': buy_venue,
                            'sell_venue': sell_venue,
                            'buy_price': buy_price,
                            'sell_price': sell_price,
                            'profit_pct': profit_pct,
                            'estimated_costs': total_costs,
                            'net_profit': net_profit,
                            'amount': amount
                        })
        
        return sorted(opportunities, key=lambda x: x['net_profit'], reverse=True)
