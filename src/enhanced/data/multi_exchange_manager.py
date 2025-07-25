"""Enhanced exchange manager supporting 50+ exchanges with latency monitoring"""
import asyncio
import time
from typing import Dict, List, Optional
from decimal import Decimal
import ccxt.pro as ccxt
import redis.asyncio as redis
from loguru import logger
import json

class EnhancedExchangeManager:
    def __init__(self):
        self.exchanges = {}
        self.latencies = {}
        self.redis_cluster = None
        self.connection_health = {}
        self.orderbook_cache = {}
        
        # Tier 1: Major Exchanges (< 50ms latency target)
        self.tier1_exchanges = [
            'binance', 'coinbase', 'kraken', 'huobi', 'okx', 'kucoin', 'bybit'
        ]
        
        # Tier 2: Regional Powerhouses (< 100ms latency target)
        self.tier2_exchanges = [
            'gate', 'mexc', 'bitget', 'cryptocom', 'bitfinex', 'ascendex'
        ]
        
        # Tier 3: Emerging/Niche (< 200ms latency target)
        self.tier3_exchanges = [
            'bingx', 'bitmart', 'whitebit', 'lbank', 'probit', 'xt',
            'coincheck', 'liquid', 'bithumb', 'upbit', 'mercado', 'wazirx',
            'bitstamp', 'gemini', 'bittrex', 'poloniex', 'hitbtc'
        ]
    
    async def initialize(self):
        """Initialize all exchange connections and Redis cluster"""
        await self.initialize_redis_cluster()
        await self.initialize_all_exchanges()
        asyncio.create_task(self.monitor_exchange_health())
        
    async def initialize_redis_cluster(self):
        """Setup Redis cluster for distributed caching"""
        self.redis_cluster = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True
        )
        logger.info("Redis cluster initialized")
    
    async def initialize_all_exchanges(self):
        """Initialize connections to all supported exchanges"""
        all_exchanges = self.tier1_exchanges + self.tier2_exchanges + self.tier3_exchanges
        
        tasks = []
        for exchange_id in all_exchanges:
            task = asyncio.create_task(self._initialize_exchange(exchange_id))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"Initialized {successful}/{len(all_exchanges)} exchanges")
    
    async def _initialize_exchange(self, exchange_id: str):
        """Initialize individual exchange with tier-specific config"""
        try:
            exchange_class = getattr(ccxt, exchange_id)
            
            # Tier-specific configuration
            if exchange_id in self.tier1_exchanges:
                timeout = 5000
                rate_limit = True
            elif exchange_id in self.tier2_exchanges:
                timeout = 10000
                rate_limit = True
            else:
                timeout = 20000
                rate_limit = True
            
            config = {
                'apiKey': '',  # Load from secure config
                'secret': '',
                'sandbox': False,
                'enableRateLimit': rate_limit,
                'timeout': timeout,
                'options': {
                    'defaultType': 'spot',
                    'adjustForTimeDifference': True
                }
            }
            
            exchange = exchange_class(config)
            self.exchanges[exchange_id] = exchange
            self.connection_health[exchange_id] = True
            
            # Start latency monitoring for this exchange
            asyncio.create_task(self._monitor_exchange_latency(exchange_id))
            
            logger.success(f"Initialized {exchange_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize {exchange_id}: {e}")
            self.connection_health[exchange_id] = False
            return False
    
    async def _monitor_exchange_latency(self, exchange_id: str):
        """Continuously monitor latency to exchange"""
        while True:
            try:
                start_time = time.time()
                
                # Use a lightweight operation to measure latency
                if exchange_id in self.exchanges:
                    await self.exchanges[exchange_id].fetch_ticker('BTC/USDT')
                
                latency = (time.time() - start_time) * 1000
                self.latencies[exchange_id] = latency
                
                # Store latency data in Redis for analysis
                await self.redis_cluster.zadd(
                    f"latency:{exchange_id}",
                    {str(time.time()): latency}
                )
                
                # Check latency thresholds
                if exchange_id in self.tier1_exchanges and latency > 50:
                    logger.warning(f"Tier 1 {exchange_id} high latency: {latency:.2f}ms")
                elif exchange_id in self.tier2_exchanges and latency > 100:
                    logger.warning(f"Tier 2 {exchange_id} high latency: {latency:.2f}ms")
                elif latency > 200:
                    logger.warning(f"Tier 3 {exchange_id} high latency: {latency:.2f}ms")
                
                self.connection_health[exchange_id] = True
                
            except Exception as e:
                logger.error(f"Latency check failed for {exchange_id}: {e}")
                self.connection_health[exchange_id] = False
            
            await asyncio.sleep(30)
    
    async def monitor_exchange_health(self):
        """Monitor overall exchange health and connectivity"""
        while True:
            healthy_tier1 = sum(1 for ex in self.tier1_exchanges if self.connection_health.get(ex, False))
            healthy_tier2 = sum(1 for ex in self.tier2_exchanges if self.connection_health.get(ex, False))
            healthy_tier3 = sum(1 for ex in self.tier3_exchanges if self.connection_health.get(ex, False))
            
            total_healthy = healthy_tier1 + healthy_tier2 + healthy_tier3
            total_exchanges = len(self.tier1_exchanges) + len(self.tier2_exchanges) + len(self.tier3_exchanges)
            
            health_percentage = (total_healthy / total_exchanges) * 100
            
            logger.info(f"Exchange Health: {health_percentage:.1f}% ({total_healthy}/{total_exchanges})")
            logger.info(f"Tier 1: {healthy_tier1}/{len(self.tier1_exchanges)}, "
                       f"Tier 2: {healthy_tier2}/{len(self.tier2_exchanges)}, "
                       f"Tier 3: {healthy_tier3}/{len(self.tier3_exchanges)}")
            
            if health_percentage < 70:
                logger.error("Critical: Exchange connectivity below 70%")
            
            await asyncio.sleep(60)
    
    async def get_all_orderbooks(self, symbol: str) -> Dict:
        """Fetch orderbooks from all healthy exchanges"""
        orderbooks = {}
        
        tasks = []
        for exchange_id, exchange in self.exchanges.items():
            if self.connection_health.get(exchange_id, False):
                task = asyncio.create_task(self._fetch_orderbook_safe(exchange_id, symbol))
                tasks.append((exchange_id, task))
        
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        for (exchange_id, _), result in zip(tasks, results):
            if not isinstance(result, Exception) and result:
                orderbooks[exchange_id] = result
        
        return orderbooks
    
    async def _fetch_orderbook_safe(self, exchange_id: str, symbol: str):
        """Safely fetch orderbook with error handling"""
        try:
            exchange = self.exchanges[exchange_id]
            orderbook = await exchange.fetch_order_book(symbol, limit=20)
            
            # Cache in Redis
            cache_key = f"orderbook:{exchange_id}:{symbol}"
            cache_data = {
                'bids': orderbook['bids'][:10],
                'asks': orderbook['asks'][:10],
                'timestamp': orderbook['timestamp'],
                'exchange': exchange_id,
                'symbol': symbol
            }
            
            await self.redis_cluster.set(
                cache_key,
                json.dumps(cache_data, default=str),
                ex=30
            )
            
            return cache_data
            
        except Exception as e:
            logger.debug(f"Failed to fetch {symbol} from {exchange_id}: {e}")
            return None
    
    async def get_average_latency(self, exchange_id: str, window_minutes: int = 5) -> Optional[float]:
        """Get average latency for an exchange over time window"""
        try:
            end_time = time.time()
            start_time = end_time - (window_minutes * 60)
            
            latencies = await self.redis_cluster.zrangebyscore(
                f"latency:{exchange_id}",
                start_time,
                end_time,
                withscores=True
            )
            
            if latencies:
                values = [float(score) for _, score in latencies]
                return sum(values) / len(values)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get average latency for {exchange_id}: {e}")
            return None
    
    async def close_all_connections(self):
        """Gracefully close all exchange connections"""
        for exchange in self.exchanges.values():
            try:
                await exchange.close()
            except Exception as e:
                logger.error(f"Error closing exchange connection: {e}")
        
        if self.redis_cluster:
            await self.redis_cluster.close()
