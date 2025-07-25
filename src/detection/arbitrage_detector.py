import asyncio
import json
import numpy as np
from typing import Dict, List, Tuple, Optional
import redis.asyncio as redis
from loguru import logger
from src.config import settings, TRADING_PAIRS
from src.data.exchange_connector import ExchangeConnector
from src.dex.web3_connector import Web3Connector

class ArbitrageDetector:
   def __init__(self):
       self.redis_client = None
       self.exchange_connector = ExchangeConnector()
       self.web3_connector = Web3Connector()
       self.min_profit_threshold = 0.005
       self.opportunities = []
       
   async def initialize(self):
       self.redis_client = redis.Redis(
           host=settings.redis_host,
           port=settings.redis_port,
           db=settings.redis_db,
           decode_responses=True
       )
       
       await self.exchange_connector.initialize()
       await self.web3_connector.initialize()
   
   async def detect_spatial_arbitrage(self, symbol: str) -> List[Dict]:
       orderbooks = await self.exchange_connector.get_all_orderbooks(symbol)
       opportunities = []
       
       exchanges = list(orderbooks.keys())
       for i in range(len(exchanges)):
           for j in range(i + 1, len(exchanges)):
               exchange_a = exchanges[i]
               exchange_b = exchanges[j]
               
               ob_a = orderbooks[exchange_a]
               ob_b = orderbooks[exchange_b]
               
               if not ob_a['asks'] or not ob_b['bids']:
                   continue
               
               best_ask_a = ob_a['asks'][0][0]
               best_bid_b = ob_b['bids'][0][0]
               
               if best_bid_b > best_ask_a:
                   profit_pct = (best_bid_b - best_ask_a) / best_ask_a
                   if profit_pct > self.min_profit_threshold:
                       opportunities.append({
                           'type': 'spatial',
                           'symbol': symbol,
                           'buy_exchange': exchange_a,
                           'sell_exchange': exchange_b,
                           'buy_price': best_ask_a,
                           'sell_price': best_bid_b,
                           'profit_pct': profit_pct,
                           'timestamp': max(ob_a['timestamp'], ob_b['timestamp'])
                       })
       
       return opportunities
   
   async def detect_triangular_arbitrage(self, base_currency: str = 'USDT') -> List[Dict]:
       opportunities = []
       symbols = [pair for pair in TRADING_PAIRS if base_currency in pair]
       
       for exchange_id in self.exchange_connector.exchanges.keys():
           triangular_opps = await self._find_triangular_opportunities(exchange_id, symbols, base_currency)
           opportunities.extend(triangular_opps)
       
       return opportunities
   
   async def _find_triangular_opportunities(self, exchange_id: str, symbols: List[str], base: str) -> List[Dict]:
       opportunities = []
       orderbooks = {}
       
       for symbol in symbols:
           ob = await self.exchange_connector.get_orderbook(exchange_id, symbol)
           if ob and ob['bids'] and ob['asks']:
               orderbooks[symbol] = ob
       
       currencies = set()
       for symbol in orderbooks.keys():
           parts = symbol.split('/')
           currencies.update(parts)
       
       currencies = list(currencies - {base})
       
       for curr_a in currencies:
           for curr_b in currencies:
               if curr_a != curr_b:
                   pair1 = f"{curr_a}/{base}"
                   pair2 = f"{curr_b}/{base}"
                   pair3 = f"{curr_a}/{curr_b}"
                   
                   if all(pair in orderbooks for pair in [pair1, pair2, pair3]):
                       opp = self._calculate_triangular_profit(
                           orderbooks[pair1], orderbooks[pair2], orderbooks[pair3],
                           curr_a, curr_b, base, exchange_id
                       )
                       if opp:
                           opportunities.append(opp)
       
       return opportunities
   
   def _calculate_triangular_profit(self, ob1: Dict, ob2: Dict, ob3: Dict, 
                                  curr_a: str, curr_b: str, base: str, exchange: str) -> Optional[Dict]:
       try:
           start_amount = 1000
           
           sell_a_price = ob1['bids'][0][0]
           amount_base = start_amount * sell_a_price
           
           buy_b_price = ob2['asks'][0][0]
           amount_b = amount_base / buy_b_price
           
           sell_b_price = ob3['bids'][0][0]
           final_amount = amount_b * sell_b_price
           
           profit_pct = (final_amount - start_amount) / start_amount
           
           if profit_pct > self.min_profit_threshold:
               return {
                   'type': 'triangular',
                   'exchange': exchange,
                   'path': [curr_a, base, curr_b, curr_a],
                   'profit_pct': profit_pct,
                   'start_amount': start_amount,
                   'final_amount': final_amount,
                   'timestamp': max(ob1['timestamp'], ob2['timestamp'], ob3['timestamp'])
               }
       except (IndexError, ZeroDivisionError, TypeError):
           pass
       
       return None
   
   async def detect_cross_chain_arbitrage(self, token_address_map: Dict[str, Dict[str, str]]) -> List[Dict]:
       opportunities = []
       
       for token_symbol, addresses in token_address_map.items():
           chains = list(addresses.keys())
           
           for i in range(len(chains)):
               for j in range(i + 1, len(chains)):
                   chain_a = chains[i]
                   chain_b = chains[j]
                   
                   price_a = await self._get_dex_token_price(chain_a, addresses[chain_a])
                   price_b = await self._get_dex_token_price(chain_b, addresses[chain_b])
                   
                   if price_a and price_b:
                       if price_b > price_a:
                           profit_pct = (price_b - price_a) / price_a
                           if profit_pct > self.min_profit_threshold:
                               opportunities.append({
                                   'type': 'cross_chain',
                                   'token': token_symbol,
                                   'buy_chain': chain_a,
                                   'sell_chain': chain_b,
                                   'buy_price': price_a,
                                   'sell_price': price_b,
                                   'profit_pct': profit_pct,
                                   'timestamp': asyncio.get_event_loop().time()
                               })
       
       return opportunities
   
   async def _get_dex_token_price(self, chain_id: str, token_address: str) -> Optional[float]:
       usdt_addresses = {
           'ethereum': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
           'bsc': '0x55d398326f99059fF775485246999027B3197955',
           'polygon': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F'
       }
       
       if chain_id not in usdt_addresses:
           return None
       
       usdt_address = usdt_addresses[chain_id]
       dex_names = list(self.web3_connector.factory_contracts.get(chain_id, {}).keys())
       
       for dex_name in dex_names:
           try:
               amount_out = await self.web3_connector.calculate_dex_price(
                   chain_id, dex_name, token_address, usdt_address, 10**18
               )
               if amount_out:
                   return amount_out / 10**6
           except Exception as e:
               logger.debug(f"Price calculation failed for {token_address} on {dex_name}: {e}")
       
       return None
   
   async def run_detection_loop(self):
       while True:
           try:
               all_opportunities = []
               
               for symbol in TRADING_PAIRS:
                   spatial_opps = await self.detect_spatial_arbitrage(symbol)
                   all_opportunities.extend(spatial_opps)
               
               triangular_opps = await self.detect_triangular_arbitrage()
               all_opportunities.extend(triangular_opps)
               
               for opp in all_opportunities:
                   key = f"opportunity:{opp['type']}:{hash(str(opp))}"
                   await self.redis_client.set(key, json.dumps(opp), ex=300)
                   logger.info(f"Found {opp['type']} opportunity: {opp.get('profit_pct', 0):.4f}")
               
               self.opportunities = all_opportunities
               
           except Exception as e:
               logger.error(f"Detection loop error: {e}")
           
           await asyncio.sleep(1)
   
   async def get_opportunities(self, min_profit: float = 0.001) -> List[Dict]:
       return [opp for opp in self.opportunities if opp.get('profit_pct', 0) >= min_profit]
   
   async def close(self):
       await self.exchange_connector.close()
       await self.web3_connector.close()
       if self.redis_client:
           await self.redis_client.close()
