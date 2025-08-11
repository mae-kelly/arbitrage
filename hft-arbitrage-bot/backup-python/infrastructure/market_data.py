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
from asyncio_throttle import Throttler

@dataclass
class TickerData:
    symbol: str
    bid: float
    ask: float
    last: float
    volume: float
    timestamp: float
    exchange: str
    tier: int = 1

@dataclass
class OrderBookData:
    symbol: str
    bids: List[List[float]]
    asks: List[List[float]]
    timestamp: float
    exchange: str
    tier: int = 1

@dataclass
class ExchangeHealth:
    exchange: str
    is_healthy: bool
    last_response_time: float
    error_count: int
    last_error: Optional[str]
    uptime_percentage: float

class EnhancedMarketDataService:
    def __init__(self, config: Dict):
        self.config = config
        self.redis_client = None
        self.websocket_connections = {}
        self.subscribers = {}
        self.running = False
        self.exchange_health = {}
        self.throttlers = {}
        
        # Initialize throttlers for each exchange tier
        for exchange_name, exchange_config in config.get('exchanges', {}).items():
            interval_ms = exchange_config.get('poll_interval_ms', 1000)
            max_rate = 1000 / interval_ms  # requests per second
            self.throttlers[exchange_name] = Throttler(rate_limit=max_rate, period=1)
            
            # Initialize health tracking
            self.exchange_health[exchange_name] = ExchangeHealth(
                exchange=exchange_name,
                is_healthy=True,
                last_response_time=0,
                error_count=0,
                last_error=None,
                uptime_percentage=100.0
            )
        
    async def initialize(self):
        redis_url = self.config.get('redis_url', 'redis://localhost:6379')
        self.redis_client = redis.from_url(redis_url)
        
        await self.setup_exchange_connections()
        
        # Start health monitoring
        asyncio.create_task(self.monitor_exchange_health())
        
    async def setup_exchange_connections(self):
        exchanges = self.config.get('exchanges', {})
        
        # Group exchanges by tier for priority handling
        tier_1_exchanges = []
        tier_2_exchanges = []
        tier_3_exchanges = []
        
        for exchange_name, exchange_config in exchanges.items():
            tier = exchange_config.get('tier', 3)
            if tier == 1:
                tier_1_exchanges.append((exchange_name, exchange_config))
            elif tier == 2:
                tier_2_exchanges.append((exchange_name, exchange_config))
            else:
                tier_3_exchanges.append((exchange_name, exchange_config))
        
        # Start tier 1 exchanges first (most important)
        for exchange_name, config in tier_1_exchanges:
            if config.get('websocket_enabled', True):
                asyncio.create_task(self.connect_exchange_websocket(exchange_name, config))
                await asyncio.sleep(0.1)  # Stagger connections
        
        # Then tier 2
        await asyncio.sleep(1)
        for exchange_name, config in tier_2_exchanges:
            if config.get('websocket_enabled', True):
                asyncio.create_task(self.connect_exchange_websocket(exchange_name, config))
                await asyncio.sleep(0.2)
        
        # Finally tier 3
        await asyncio.sleep(2)
        for exchange_name, config in tier_3_exchanges:
            if config.get('websocket_enabled', True):
                asyncio.create_task(self.connect_exchange_websocket(exchange_name, config))
                await asyncio.sleep(0.5)
    
    async def connect_exchange_websocket(self, exchange_name: str, config: Dict):
        ws_url = config.get('websocket_url')
        if not ws_url:
            logging.info(f"No WebSocket URL for {exchange_name}, using REST only")
            return
            
        while self.running:
            try:
                async with self.throttlers[exchange_name]:
                    start_time = time.time()
                    
                    async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as websocket:
                        self.websocket_connections[exchange_name] = websocket
                        
                        # Record successful connection
                        response_time = time.time() - start_time
                        await self.update_exchange_health(exchange_name, True, response_time)
                        
                        subscribe_message = self.build_subscribe_message(exchange_name, config)
                        if subscribe_message:
                            await websocket.send(json.dumps(subscribe_message))
                        
                        logging.info(f"✅ Connected to {exchange_name} WebSocket")
                        
                        async for message in websocket:
                            await self.process_websocket_message(exchange_name, message)
                            
            except Exception as e:
                await self.update_exchange_health(exchange_name, False, 0, str(e))
                logging.error(f"❌ WebSocket error for {exchange_name}: {e}")
                
                # Exponential backoff based on tier
                tier = config.get('tier', 3)
                base_delay = [1, 3, 10][tier - 1]  # tier 1: 1s, tier 2: 3s, tier 3: 10s
                await asyncio.sleep(base_delay + min(self.exchange_health[exchange_name].error_count, 10))
    
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
        
        elif exchange_name == 'bybit':
            return {
                "op": "subscribe",
                "args": [f"tickers.{symbol.replace('/', '')}" for symbol in symbols]
            }
        
        elif exchange_name == 'okx':
            return {
                "op": "subscribe",
                "args": [{"channel": "tickers", "instId": symbol.replace('/', '-')} for symbol in symbols]
            }
        
        elif exchange_name == 'kucoin':
            return {
                "type": "subscribe",
                "topic": "/market/ticker:" + ",".join(symbols),
                "response": True
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
            elif exchange_name == 'bybit':
                await self.process_bybit_message(data)
            elif exchange_name == 'okx':
                await self.process_okx_message(data)
            elif exchange_name == 'kucoin':
                await self.process_kucoin_message(data)
                
        except Exception as e:
            logging.error(f"Error processing message from {exchange_name}: {e}")
    
    async def process_binance_message(self, data: Dict):
        if 'stream' in data and 'data' in data:
            stream = data['stream']
            msg_data = data['data']
            
            if '@ticker' in stream:
                symbol = self.normalize_symbol(stream.split('@')[0].upper())
                
                ticker = TickerData(
                    symbol=symbol,
                    bid=float(msg_data['b']),
                    ask=float(msg_data['a']),
                    last=float(msg_data['c']),
                    volume=float(msg_data['v']),
                    timestamp=time.time(),
                    exchange='binance',
                    tier=1
                )
                
                await self.publish_ticker_data(ticker)
    
    async def process_bybit_message(self, data: Dict):
        if data.get('topic', '').startswith('tickers'):
            msg_data = data.get('data', {})
            symbol = self.normalize_symbol(msg_data.get('symbol', ''))
            
            ticker = TickerData(
                symbol=symbol,
                bid=float(msg_data.get('bid1Price', 0)),
                ask=float(msg_data.get('ask1Price', 0)),
                last=float(msg_data.get('lastPrice', 0)),
                volume=float(msg_data.get('volume24h', 0)),
                timestamp=time.time(),
                exchange='bybit',
                tier=1
            )
            
            await self.publish_ticker_data(ticker)
    
    async def process_okx_message(self, data: Dict):
        if data.get('arg', {}).get('channel') == 'tickers':
            for msg_data in data.get('data', []):
                symbol = self.normalize_symbol(msg_data.get('instId', '').replace('-', '/'))
                
                ticker = TickerData(
                    symbol=symbol,
                    bid=float(msg_data.get('bidPx', 0)),
                    ask=float(msg_data.get('askPx', 0)),
                    last=float(msg_data.get('last', 0)),
                    volume=float(msg_data.get('vol24h', 0)),
                    timestamp=time.time(),
                    exchange='okx',
                    tier=1
                )
                
                await self.publish_ticker_data(ticker)
    
    def normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol format across exchanges"""
        # Remove common variations and standardize
        symbol = symbol.upper()
        if '-' in symbol:
            symbol = symbol.replace('-', '/')
        elif len(symbol) >= 6 and '/' not in symbol:
            # Assume first 3 chars are base, rest is quote
            symbol = f"{symbol[:3]}/{symbol[3:]}"
        return symbol
    
    async def update_exchange_health(self, exchange: str, is_healthy: bool, response_time: float, error: str = None):
        health = self.exchange_health[exchange]
        health.is_healthy = is_healthy
        health.last_response_time = response_time
        
        if not is_healthy:
            health.error_count += 1
            health.last_error = error
        else:
            health.error_count = max(0, health.error_count - 1)  # Slowly recover
        
        # Calculate uptime (simplified)
        if health.error_count == 0:
            health.uptime_percentage = min(100.0, health.uptime_percentage + 0.1)
        else:
            health.uptime_percentage = max(0.0, health.uptime_percentage - 1.0)
    
    async def monitor_exchange_health(self):
        """Periodically check exchange health and disable problematic ones"""
        while self.running:
            try:
                monitoring_config = self.config.get('monitoring', {})
                max_failures = monitoring_config.get('max_api_failures', 5)
                auto_disable = monitoring_config.get('auto_disable_failed_exchanges', True)
                
                for exchange_name, health in self.exchange_health.items():
                    if auto_disable and health.error_count >= max_failures:
                        logging.warning(f"🚫 Auto-disabling {exchange_name} due to {health.error_count} failures")
                        # Could implement exchange disabling logic here
                
                # Log health summary
                healthy_exchanges = sum(1 for h in self.exchange_health.values() if h.is_healthy)
                total_exchanges = len(self.exchange_health)
                logging.info(f"🏥 Exchange Health: {healthy_exchanges}/{total_exchanges} healthy")
                
                await asyncio.sleep(monitoring_config.get('exchange_health_check_interval', 30))
                
            except Exception as e:
                logging.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(10)
    
    async def get_all_exchange_prices(self, symbol: str) -> Dict[str, TickerData]:
        """Get prices from all healthy exchanges for a symbol"""
        results = {}
        
        tasks = []
        for exchange_name, health in self.exchange_health.items():
            if health.is_healthy:
                tasks.append(self.get_latest_ticker(exchange_name, symbol))
        
        if tasks:
            tickers = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, ticker in enumerate(tickers):
                if isinstance(ticker, TickerData):
                    exchange_name = list(self.exchange_health.keys())[i]
                    results[exchange_name] = ticker
        
        return results
    
    async def calculate_comprehensive_arbitrage_opportunities(self, symbol: str) -> List[Dict]:
        """Calculate arbitrage opportunities across ALL exchanges"""
        prices = await self.get_all_exchange_prices(symbol)
        opportunities = []
        
        # Check every exchange pair combination
        exchanges = list(prices.keys())
        for i in range(len(exchanges)):
            for j in range(i + 1, len(exchanges)):
                exchange1, exchange2 = exchanges[i], exchanges[j]
                ticker1, ticker2 = prices[exchange1], prices[exchange2]
                
                # Direction 1: Buy on exchange1, sell on exchange2
                if ticker1.ask < ticker2.bid:
                    profit_percentage = ((ticker2.bid - ticker1.ask) / ticker1.ask) * 100
                    
                    # Adjust profit threshold by exchange tier
                    tier_thresholds = self.config.get('trading', {}).get('tier_profit_thresholds', {})
                    min_profit = tier_thresholds.get(f"tier_{ticker1.tier}", 0.1)
                    
                    if profit_percentage > min_profit:
                        opportunities.append({
                            'buy_exchange': exchange1,
                            'sell_exchange': exchange2,
                            'buy_price': ticker1.ask,
                            'sell_price': ticker2.bid,
                            'profit_percentage': profit_percentage,
                            'symbol': symbol,
                            'volume': min(ticker1.volume, ticker2.volume),
                            'tier_1_exchange': ticker1.tier,
                            'tier_2_exchange': ticker2.tier,
                            'confidence': self.calculate_opportunity_confidence(ticker1, ticker2)
                        })
                
                # Direction 2: Buy on exchange2, sell on exchange1
                if ticker2.ask < ticker1.bid:
                    profit_percentage = ((ticker1.bid - ticker2.ask) / ticker2.ask) * 100
                    
                    min_profit = tier_thresholds.get(f"tier_{ticker2.tier}", 0.1)
                    
                    if profit_percentage > min_profit:
                        opportunities.append({
                            'buy_exchange': exchange2,
                            'sell_exchange': exchange1,
                            'buy_price': ticker2.ask,
                            'sell_price': ticker1.bid,
                            'profit_percentage': profit_percentage,
                            'symbol': symbol,
                            'volume': min(ticker1.volume, ticker2.volume),
                            'tier_1_exchange': ticker2.tier,
                            'tier_2_exchange': ticker1.tier,
                            'confidence': self.calculate_opportunity_confidence(ticker2, ticker1)
                        })
        
        # Sort by profit percentage and confidence
        opportunities.sort(key=lambda x: (x['profit_percentage'] * x['confidence']), reverse=True)
        return opportunities
    
    def calculate_opportunity_confidence(self, ticker1: TickerData, ticker2: TickerData) -> float:
        """Calculate confidence score for arbitrage opportunity"""
        confidence = 1.0
        
        # Reduce confidence for lower tier exchanges
        if ticker1.tier > 1 or ticker2.tier > 1:
            confidence *= 0.8
        
        # Reduce confidence for low volume
        min_volume = min(ticker1.volume, ticker2.volume)
        if min_volume < 10:
            confidence *= 0.5
        elif min_volume < 100:
            confidence *= 0.8
        
        # Increase confidence for tier 1 exchanges
        if ticker1.tier == 1 and ticker2.tier == 1:
            confidence *= 1.2
        
        return min(confidence, 1.0)
    
    # ... (rest of the original methods: publish_ticker_data, get_latest_ticker, etc.)
    
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
    
    async def get_latest_ticker(self, exchange: str, symbol: str) -> Optional[TickerData]:
        key = f"ticker:{exchange}:{symbol}"
        data = await self.redis_client.get(key)
        
        if data:
            ticker_dict = json.loads(data)
            return TickerData(**ticker_dict)
        
        return await self.fetch_ticker_rest(exchange, symbol)
    
    async def fetch_ticker_rest(self, exchange: str, symbol: str) -> Optional[TickerData]:
        # Implementation for REST API fallback
        # ... (implement for each exchange)
        return None
    
    async def start(self):
        self.running = True
        await self.initialize()
        logging.info(f"🚀 Enhanced market data service started with {len(self.config.get('exchanges', {}))} exchanges")
    
    async def stop(self):
        self.running = False
        
        for websocket in self.websocket_connections.values():
            await websocket.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logging.info("🛑 Market data service stopped")

# Keep the original class for backward compatibility
MarketDataService = EnhancedMarketDataService
