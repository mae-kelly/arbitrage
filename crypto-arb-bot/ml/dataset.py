import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta

class RealTimeDataset:
    def __init__(self):
        self.price_history = {}
        self.volume_history = {}
        self.liquidity_history = {}
        self.endpoints = {
            'uniswap_v3': 'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3',
            'sushiswap': 'https://api.thegraph.com/subgraphs/name/sushiswap/exchange',
            'pancakeswap': 'https://api.thegraph.com/subgraphs/name/pancakeswap/exchange-v2',
            'quickswap': 'https://api.thegraph.com/subgraphs/name/sameepsi/quickswap-v3',
        }
        
    async def fetch_pool_data(self, endpoint: str, query: str) -> Dict:
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json={'query': query}) as response:
                return await response.json()
                
    async def get_realtime_prices(self) -> Dict[str, Dict]:
        query = '''
        {
            pools(first: 100, orderBy: totalValueLockedUSD, orderDirection: desc) {
                id
                token0 { symbol, id, decimals }
                token1 { symbol, id, decimals }
                token0Price
                token1Price
                totalValueLockedUSD
                volumeUSD
                feeTier
            }
        }
        '''
        
        tasks = []
        for name, endpoint in self.endpoints.items():
            tasks.append(self.fetch_pool_data(endpoint, query))
            
        results = await asyncio.gather(*tasks)
        
        prices = {}
        for i, (name, _) in enumerate(self.endpoints.items()):
            if 'data' in results[i] and 'pools' in results[i]['data']:
                for pool in results[i]['data']['pools']:
                    key = f"{name}_{pool['token0']['symbol']}_{pool['token1']['symbol']}"
                    prices[key] = {
                        'price0': float(pool['token0Price']),
                        'price1': float(pool['token1Price']),
                        'liquidity': float(pool['totalValueLockedUSD']),
                        'volume': float(pool['volumeUSD']),
                        'fee': int(pool.get('feeTier', 3000)),
                    }
        
        return prices
        
    def create_features(self, prices: Dict[str, Dict]) -> np.ndarray:
        features = []
        
        for key, data in prices.items():
            feature_vec = [
                data['price0'],
                data['price1'],
                data['liquidity'],
                data['volume'],
                data['fee'] / 10000,
                np.log(data['price0'] + 1),
                np.log(data['price1'] + 1),
                np.log(data['liquidity'] + 1),
                np.log(data['volume'] + 1),
            ]
            
            if key in self.price_history:
                history = self.price_history[key]
                feature_vec.extend([
                    (data['price0'] - history[-1]) / history[-1] if history[-1] > 0 else 0,
                    np.std(history) if len(history) > 1 else 0,
                    np.mean(history) if len(history) > 0 else 0,
                ])
            else:
                feature_vec.extend([0, 0, 0])
                
            features.append(feature_vec)
            
            if key not in self.price_history:
                self.price_history[key] = []
            self.price_history[key].append(data['price0'])
            if len(self.price_history[key]) > 100:
                self.price_history[key].pop(0)
                
        return np.array(features, dtype=np.float32)
        
    async def get_training_batch(self, batch_size: int = 32) -> Tuple[np.ndarray, np.ndarray]:
        prices = await self.get_realtime_prices()
        features = self.create_features(prices)
        
        if len(features) < batch_size:
            features = np.pad(features, ((0, batch_size - len(features)), (0, 0)), mode='constant')
            
        labels = np.random.randint(0, 3, size=(batch_size,))
        
        return features[:batch_size], labels
