import asyncio
import ccxt.pro as ccxt
import redis.asyncio as redis
import json
from typing import Dict, List, Optional
from loguru import logger
from decimal import Decimal
from datetime import datetime

class ExchangeManager:
    def __init__(self):
        self.exchanges = {}
        self.redis_client = None
        self.symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        
    async def initialize(self):
        """Initialize exchange connections and Redis"""
        self.redis_client = redis.Redis(
            host='localhost', port=6379, db=0, decode_responses=True
        )
        
        # Initialize major exchanges
        exchange_configs = {
            'binance': {'apiKey': '', 'secret': '', 'sandbox': False},
            'coinbase': {'apiKey': '', 'secret': '', 'sandbox': False},
            'kraken': {'apiKey': '', 'secret': '', 'sandbox': False},
        }
        
        for exchange_id, config in exchange_configs.items():
            try:
                exchange_class = getattr(ccxt, exchange_id)
                self.exchanges[exchange_id] = exchange_class({
                    **config,
                    'enableRateLimit': True,
                    'timeout': 30000,
                })
                logger.info(f"Initialized {exchange_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize {exchange_id}: {e}")
    
    async def fetch_orderbook(self, exchange_id: str, symbol: str) -> Optional[Dict]:
        """Fetch orderbook from specific exchange"""
        if exchange_id not in self.exchanges:
            return None
            
        try:
            exchange = self.exchanges[exchange_id]
            orderbook = await exchange.fetch_order_book(symbol, limit=10)
            
            # Store in Redis
            key = f"orderbook:{exchange_id}:{symbol}"
            data = {
                'exchange': exchange_id,
                'symbol': symbol,
                'bids': orderbook['bids'][:10],
                'asks': orderbook['asks'][:10],
                'timestamp': datetime.now().isoformat()
            }
            await self.redis_client.set(key, json.dumps(data), ex=60)
            
            return data
        except Exception as e:
            logger.error(f"Error fetching {symbol} from {exchange_id}: {e}")
            return None
    
    async def monitor_prices(self):
        """Continuously monitor prices across exchanges"""
        while True:
            tasks = []
            for exchange_id in self.exchanges.keys():
                for symbol in self.symbols:
                    task = asyncio.create_task(
                        self.fetch_orderbook(exchange_id, symbol)
                    )
                    tasks.append(task)
            
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(1)  # Update every second
    
    async def get_all_orderbooks(self, symbol: str) -> Dict[str, Dict]:
        """Get all orderbooks for a symbol from Redis"""
        orderbooks = {}
        for exchange_id in self.exchanges.keys():
            key = f"orderbook:{exchange_id}:{symbol}"
            data = await self.redis_client.get(key)
            if data:
                orderbooks[exchange_id] = json.loads(data)
        return orderbooks
    
    async def close(self):
        """Close all connections"""
        for exchange in self.exchanges.values():
            await exchange.close()
        if self.redis_client:
            await self.redis_client.close()
