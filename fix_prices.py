import json
import asyncio
from web3 import Web3
from decimal import Decimal
import aiohttp

UNISWAP_V2_FACTORY = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
UNISWAP_V3_FACTORY = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
SUSHISWAP_FACTORY = "0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac"

UNISWAP_V2_PAIR_ABI = json.loads('[{"constant":true,"inputs":[],"name":"getReserves","outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},{"internalType":"uint112","name":"_reserve1","type":"uint112"},{"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"token0","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"token1","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"}]')

UNISWAP_V3_POOL_ABI = json.loads('[{"inputs":[],"name":"slot0","outputs":[{"internalType":"uint160","name":"sqrtPriceX96","type":"uint160"},{"internalType":"int24","name":"tick","type":"int24"},{"internalType":"uint16","name":"observationIndex","type":"uint16"},{"internalType":"uint16","name":"observationCardinality","type":"uint16"},{"internalType":"uint16","name":"observationCardinalityNext","type":"uint16"},{"internalType":"uint8","name":"feeProtocol","type":"uint8"},{"internalType":"bool","name":"unlocked","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"liquidity","outputs":[{"internalType":"uint128","name":"","type":"uint128"}],"stateMutability":"view","type":"function"}]')

class RealPriceFetcher:
    def __init__(self, w3):
        self.w3 = w3
        self.factory_contracts = {
            'uniswap_v2': self.w3.eth.contract(address=UNISWAP_V2_FACTORY, abi=json.loads('[{"constant":true,"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"}],"name":"getPair","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"}]')),
            'uniswap_v3': self.w3.eth.contract(address=UNISWAP_V3_FACTORY, abi=json.loads('[{"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"},{"internalType":"uint24","name":"","type":"uint24"}],"name":"getPool","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}]'))
        }
    
    async def get_uniswap_v2_price(self, token0, token1):
        pair_address = self.factory_contracts['uniswap_v2'].functions.getPair(token0, token1).call()
        if pair_address == '0x0000000000000000000000000000000000000000':
            return None
        
        pair = self.w3.eth.contract(address=pair_address, abi=UNISWAP_V2_PAIR_ABI)
        reserves = pair.functions.getReserves().call()
        
        pair_token0 = pair.functions.token0().call()
        
        if pair_token0.lower() == token0.lower():
            reserve0, reserve1 = reserves[0], reserves[1]
        else:
            reserve0, reserve1 = reserves[1], reserves[0]
        
        if reserve0 > 0:
            price = reserve1 / reserve0
            return price
        return None
    
    async def get_uniswap_v3_price(self, token0, token1, fee=3000):
        pool_address = self.factory_contracts['uniswap_v3'].functions.getPool(token0, token1, fee).call()
        if pool_address == '0x0000000000000000000000000000000000000000':
            return None
        
        pool = self.w3.eth.contract(address=pool_address, abi=UNISWAP_V3_POOL_ABI)
        slot0 = pool.functions.slot0().call()
        sqrtPriceX96 = slot0[0]
        
        price = (sqrtPriceX96 / (2**96)) ** 2
        
        token0_decimals = 18
        token1_decimals = 6 if token1.lower() == '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48' else 18
        
        price = price * (10 ** (token0_decimals - token1_decimals))
        
        return price
    
    async def get_all_dex_prices(self, token0, token1):
        prices = {}
        
        v2_price = await self.get_uniswap_v2_price(token0, token1)
        if v2_price:
            prices['uniswap_v2'] = v2_price
        
        for fee in [500, 3000, 10000]:
            v3_price = await self.get_uniswap_v3_price(token0, token1, fee)
            if v3_price:
                prices[f'uniswap_v3_{fee}'] = v3_price
        
        return prices

async def update_price_functions():
    w3 = Web3(Web3.HTTPProvider('https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY'))
    fetcher = RealPriceFetcher(w3)
    
    weth = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
    usdc = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'
    
    prices = await fetcher.get_all_dex_prices(weth, usdc)
    print(f"Real prices: {prices}")
    
    with open('real_prices.json', 'w') as f:
        json.dump(prices, f)

if __name__ == "__main__":
    asyncio.run(update_price_functions())
