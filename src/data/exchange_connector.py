import asyncio
import websockets
import json
import ccxt.pro as ccxt
import redis.asyncio as redis
from typing import Dict, Any, List
from loguru import logger
from src.config import settings, EXCHANGES

class ExchangeConnector:
   def __init__(self):
       self.exchanges = {}
       self.redis_client = None
       self.ws_connections = {}
       self.orderbooks = {}
       
   async def initialize(self):
       self.redis_client = redis.Redis(
           host=settings.redis_host,
           port=settings.redis_port,
           db=settings.redis_db,
           decode_responses=True
       )
       
       for exchange_id in EXCHANGES:
           try:
               exchange_class = getattr(ccxt, exchange_id)
               self.exchanges[exchange_id] = exchange_class({
                   'apiKey': '',
                   'secret': '',
                   'sandbox': False,
                   'enableRateLimit': True,
               })
           except Exception as e:
               logger.warning(f"Failed to initialize {exchange_id}: {e}")
   
   async def connect_websockets(self):
       tasks = []
       for exchange_id in self.exchanges.keys():
           task = asyncio.create_task(self._connect_exchange_ws(exchange_id))
           tasks.append(task)
       
       await asyncio.gather(*tasks, return_exceptions=True)
   
   async def _connect_exchange_ws(self, exchange_id: str):
       exchange = self.exchanges[exchange_id]
       
       try:
           while True:
               try:
                   orderbook = await exchange.watch_order_book('BTC/USDT')
                   await self._process_orderbook(exchange_id, 'BTC/USDT', orderbook)
               except Exception as e:
                   logger.error(f"WebSocket error for {exchange_id}: {e}")
                   await asyncio.sleep(5)
       except Exception as e:
           logger.error(f"Failed to connect to {exchange_id}: {e}")
   
   async def _process_orderbook(self, exchange_id: str, symbol: str, orderbook: Dict):
       key = f"orderbook:{exchange_id}:{symbol}"
       
       data = {
           'exchange': exchange_id,
           'symbol': symbol,
           'timestamp': orderbook['timestamp'],
           'bids': orderbook['bids'][:10],
           'asks': orderbook['asks'][:10]
       }
       
       await self.redis_client.set(key, json.dumps(data), ex=60)
       
       if exchange_id not in self.orderbooks:
           self.orderbooks[exchange_id] = {}
       self.orderbooks[exchange_id][symbol] = data
   
   async def get_orderbook(self, exchange_id: str, symbol: str) -> Dict:
       key = f"orderbook:{exchange_id}:{symbol}"
       data = await self.redis_client.get(key)
       return json.loads(data) if data else None
   
   async def get_all_orderbooks(self, symbol: str) -> Dict[str, Dict]:
       orderbooks = {}
       for exchange_id in self.exchanges.keys():
           ob = await self.get_orderbook(exchange_id, symbol)
           if ob:
               orderbooks[exchange_id] = ob
       return orderbooks
   
   async def close(self):
       for exchange in self.exchanges.values():
           await exchange.close()
       
       if self.redis_client:
           await self.redis_client.close()
