from web3 import Web3
import aiohttp
import asyncio
from typing import Dict, List, Tuple
from decimal import Decimal
import os

class RealDataFetcher:
    def __init__(self, w3: Web3):
        self.w3 = w3
        
    async def get_pool_reserves(self, pool_address: str) -> Tuple[int, int]:
        """Get real reserves from Uniswap V2 pool"""
        pool = self.w3.eth.contract(
            address=Web3.toChecksumAddress(pool_address),
            abi=[{
                "constant": True,
                "inputs": [],
                "name": "getReserves",
                "outputs": [
                    {"name": "reserve0", "type": "uint112"},
                    {"name": "reserve1", "type": "uint112"},
                    {"name": "blockTimestampLast", "type": "uint32"}
                ],
                "type": "function"
            }]
        )
        reserves = pool.functions.getReserves().call()
        return (reserves[0], reserves[1])
    
    async def get_v3_pool_price(self, pool_address: str) -> float:
        """Get real price from Uniswap V3 pool"""
        pool = self.w3.eth.contract(
            address=Web3.toChecksumAddress(pool_address),
            abi=[{
                "inputs": [],
                "name": "slot0",
                "outputs": [
                    {"name": "sqrtPriceX96", "type": "uint160"},
                    {"name": "tick", "type": "int24"},
                    {"name": "observationIndex", "type": "uint16"},
                    {"name": "observationCardinality", "type": "uint16"},
                    {"name": "observationCardinalityNext", "type": "uint16"},
                    {"name": "feeProtocol", "type": "uint8"},
                    {"name": "unlocked", "type": "bool"}
                ],
                "type": "function"
            }]
        )
        slot0 = pool.functions.slot0().call()
        sqrt_price_x96 = slot0[0]
        price = (sqrt_price_x96 / 2**96) ** 2
        return price
