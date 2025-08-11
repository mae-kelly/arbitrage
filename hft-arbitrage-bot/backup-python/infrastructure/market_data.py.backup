import asyncio
import websockets
import json
import aiohttp
import redis.asyncio as redis
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import time
import logging

@dataclass
class TickerData:
    symbol: str
    bid: float
    ask: float
    last: float
    volume: float
    timestamp: float
    exchange: str

@dataclass
class OrderBookData:
    symbol: str
    bids: List[List[float]]
    asks: List[List[float]]
    timestamp: float
    exchange: str

class MarketDataService:
    def __init__(self, config: Dict):
        self.config = config
        self.redis_client = None
        self.websocket_connections = {}
        self.subscribers = {}
        self.running = False
        self.rate_limiters = {}
        
    async def initialize(self):
        redis_url = self.config.get('redis_url', 'redis://localhost:6379')
        self.redis_client = redis.from_url(redis_url)
        
        await self.setup_exchange_connections()
        
    async def setup_exchange_connections(self):
        exchanges = self.config.get('exchanges', {})
        
        for exchange_name, exchange_config in exchanges.items():
            if exchange_config.get('websocket_enabled', True):
                asyncio.create_task(self.connect_exchange_websocket(exchange_name, exchange_config))
    
    async def connect_exchange_websocket(self, exchange_name: str, config: Dict):
        ws_url = config.get('websocket_url')
        if not ws_url:
            return
            
        while self.running:
            try:
                async with websockets.connect(ws_url) as websocket:
                    self.websocket_connections[exchange_name] = websocket
                    
                    subscribe_message = self.build_subscribe_message(exchange_name, config)
                    if subscribe_message:
                        await websocket.send(json.dumps(subscribe_message))
                    
                    async for message in websocket:
                        await self.process_websocket_message(exchange_name, message)
                        
            except Exception as e:
                logging.error(f"WebSocket error for {exchange_name}: {e}")
                await asyncio.sleep(5)
    
    def build_subscribe_message(self, exchange_name: str, config: Dict) -> Optional[Dict]:
        symbols = config.get('symbols', [])
        
        if exchange_name == 'binance':
            streams = []
            for symbol in symbols:
                symbol_lower = symbol.lower().replace('/', '')
                streams.extend([
                    f"{symbol_lower}@ticker",
                    f"{symbol_lower}@depth20@100ms"
                ])
            return {
                "method": "SUBSCRIBE",
                "params": streams,
                "id": 1
            }
        
        elif exchange_name == 'coinbase':
            return {
                "type": "subscribe",
                "product_ids": symbols,
                "channels": ["ticker", "level2"]
            }
        
        elif exchange_name == 'kraken':
            return {
                "event": "subscribe",
                "pair": symbols,
                "subscription": {"name": "ticker"}
            }
        
        return None
    
    async def process_websocket_message(self, exchange_name: str, message: str):
        try:
            data = json.loads(message)
            
            if exchange_name == 'binance':
                await self.process_binance_message(data)
            elif exchange_name == 'coinbase':
                await self.process_coinbase_message(data)
            elif exchange_name == 'kraken':
                await self.process_kraken_message(data)
                
        except Exception as e:
            logging.error(f"Error processing message from {exchange_name}: {e}")
    
    async def process_binance_message(self, data: Dict):
        if 'stream' in data and 'data' in data:
            stream = data['stream']
            msg_data = data['data']
            
            if '@ticker' in stream:
                symbol = stream.split('@')[0].upper()
                symbol = f"{symbol[:3]}/{symbol[3:]}"
                
                ticker = TickerData(
                    symbol=symbol,
                    bid=float(msg_data['b']),
                    ask=float(msg_data['a']),
                    last=float(msg_data['c']),
                    volume=float(msg_data['v']),
                    timestamp=time.time(),
                    exchange='binance'
                )
                
                await self.publish_ticker_data(ticker)
                
            elif '@depth' in stream:
                symbol = stream.split('@')[0].upper()
                symbol = f"{symbol[:3]}/{symbol[3:]}"
                
                orderbook = OrderBookData(
                    symbol=symbol,
                    bids=[[float(b[0]), float(b[1])] for b in msg_data['bids']],
                    asks=[[float(a[0]), float(a[1])] for a in msg_data['asks']],
                    timestamp=time.time(),
                    exchange='binance'
                )
                
                await self.publish_orderbook_data(orderbook)
    
    async def process_coinbase_message(self, data: Dict):
        if data.get('type') == 'ticker':
            ticker = TickerData(
                symbol=data['product_id'],
                bid=float(data['best_bid']),
                ask=float(data['best_ask']),
                last=float(data['price']),
                volume=float(data['volume_24h']),
                timestamp=time.time(),
                exchange='coinbase'
            )
            
            await self.publish_ticker_data(ticker)
            
        elif data.get('type') == 'l2update':
            orderbook = OrderBookData(
                symbol=data['product_id'],
                bids=[[float(change[1]), float(change[2])] for change in data['changes'] if change[0] == 'buy'],
                asks=[[float(change[1]), float(change[2])] for change in data['changes'] if change[0] == 'sell'],
                timestamp=time.time(),
                exchange='coinbase'
            )
            
            await self.publish_orderbook_data(orderbook)
    
    async def process_kraken_message(self, data: Dict):
        if isinstance(data, list) and len(data) >= 4:
            if data[2] == 'ticker':
                symbol = data[3]
                ticker_data = data[1]
                
                ticker = TickerData(
                    symbol=symbol,
                    bid=float(ticker_data['b'][0]),
                    ask=float(ticker_data['a'][0]),
                    last=float(ticker_data['c'][0]),
                    volume=float(ticker_data['v'][1]),
                    timestamp=time.time(),
                    exchange='kraken'
                )
                
                await self.publish_ticker_data(ticker)
    
    async def publish_ticker_data(self, ticker: TickerData):
        key = f"ticker:{ticker.exchange}:{ticker.symbol}"
        await self.redis_client.set(key, json.dumps(asdict(ticker)), ex=60)
        await self.redis_client.publish(f"market_data:ticker", json.dumps(asdict(ticker)))
        
        if ticker.symbol in self.subscribers:
            for callback in self.subscribers[ticker.symbol]:
                try:
                    await callback(ticker)
                except Exception as e:
                    logging.error(f"Error in ticker callback: {e}")
    
    async def publish_orderbook_data(self, orderbook: OrderBookData):
        key = f"orderbook:{orderbook.exchange}:{orderbook.symbol}"
        await self.redis_client.set(key, json.dumps(asdict(orderbook)), ex=30)
        await self.redis_client.publish(f"market_data:orderbook", json.dumps(asdict(orderbook)))
    
    async def get_latest_ticker(self, exchange: str, symbol: str) -> Optional[TickerData]:
        key = f"ticker:{exchange}:{symbol}"
        data = await self.redis_client.get(key)
        
        if data:
            ticker_dict = json.loads(data)
            return TickerData(**ticker_dict)
        
        return await self.fetch_ticker_rest(exchange, symbol)
    
    async def get_latest_orderbook(self, exchange: str, symbol: str) -> Optional[OrderBookData]:
        key = f"orderbook:{exchange}:{symbol}"
        data = await self.redis_client.get(key)
        
        if data:
            orderbook_dict = json.loads(data)
            return OrderBookData(**orderbook_dict)
        
        return None
    
    async def fetch_ticker_rest(self, exchange: str, symbol: str) -> Optional[TickerData]:
        urls = {
            'binance': f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol.replace('/', '')}",
            'coinbase': f"https://api.exchange.coinbase.com/products/{symbol}/ticker",
            'kraken': f"https://api.kraken.com/0/public/Ticker?pair={symbol}"
        }
        
        if exchange not in urls:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(urls[exchange]) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self.parse_rest_ticker(exchange, symbol, data)
        except Exception as e:
            logging.error(f"Error fetching ticker from {exchange}: {e}")
        
        return None
    
    def parse_rest_ticker(self, exchange: str, symbol: str, data: Dict) -> Optional[TickerData]:
        try:
            if exchange == 'binance':
                return TickerData(
                    symbol=symbol,
                    bid=float(data['bidPrice']),
                    ask=float(data['askPrice']),
                    last=float(data['lastPrice']),
                    volume=float(data['volume']),
                    timestamp=time.time(),
                    exchange=exchange
                )
            elif exchange == 'coinbase':
                return TickerData(
                    symbol=symbol,
                    bid=float(data['bid']),
                    ask=float(data['ask']),
                    last=float(data['price']),
                    volume=float(data['volume']),
                    timestamp=time.time(),
                    exchange=exchange
                )
        except Exception as e:
            logging.error(f"Error parsing ticker data: {e}")
        
        return None
    
    def subscribe_to_symbol(self, symbol: str, callback: Callable[[TickerData], None]):
        if symbol not in self.subscribers:
            self.subscribers[symbol] = []
        self.subscribers[symbol].append(callback)
    
    def unsubscribe_from_symbol(self, symbol: str, callback: Callable[[TickerData], None]):
        if symbol in self.subscribers and callback in self.subscribers[symbol]:
            self.subscribers[symbol].remove(callback)
    
    async def get_multi_exchange_prices(self, symbol: str) -> Dict[str, TickerData]:
        results = {}
        exchanges = ['binance', 'coinbase', 'kraken']
        
        tasks = []
        for exchange in exchanges:
            tasks.append(self.get_latest_ticker(exchange, symbol))
        
        tickers = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, ticker in enumerate(tickers):
            if isinstance(ticker, TickerData):
                results[exchanges[i]] = ticker
        
        return results
    
    async def calculate_arbitrage_opportunities(self, symbol: str) -> List[Dict]:
        prices = await self.get_multi_exchange_prices(symbol)
        opportunities = []
        
        exchanges = list(prices.keys())
        for i in range(len(exchanges)):
            for j in range(i + 1, len(exchanges)):
                exchange1, exchange2 = exchanges[i], exchanges[j]
                ticker1, ticker2 = prices[exchange1], prices[exchange2]
                
                if ticker1.ask < ticker2.bid:
                    profit_percentage = ((ticker2.bid - ticker1.ask) / ticker1.ask) * 100
                    opportunities.append({
                        'buy_exchange': exchange1,
                        'sell_exchange': exchange2,
                        'buy_price': ticker1.ask,
                        'sell_price': ticker2.bid,
                        'profit_percentage': profit_percentage,
                        'symbol': symbol
                    })
                
                if ticker2.ask < ticker1.bid:
                    profit_percentage = ((ticker1.bid - ticker2.ask) / ticker2.ask) * 100
                    opportunities.append({
                        'buy_exchange': exchange2,
                        'sell_exchange': exchange1,
                        'buy_price': ticker2.ask,
                        'sell_price': ticker1.bid,
                        'profit_percentage': profit_percentage,
                        'symbol': symbol
                    })
        
        return sorted(opportunities, key=lambda x: x['profit_percentage'], reverse=True)
    
    async def start(self):
        self.running = True
        await self.initialize()
    
    async def stop(self):
        self.running = False
        
        for websocket in self.websocket_connections.values():
            await websocket.close()
        
        if self.redis_client:
            await self.redis_client.close()
