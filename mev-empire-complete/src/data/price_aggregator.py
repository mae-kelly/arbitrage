import asyncio
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
import time

logger = logging.getLogger(__name__)

class PriceAggregator:
    def __init__(self, chain_manager):
        self.chain_manager = chain_manager
        self.price_cache = {}
        self.is_running = False
        
    async def initialize(self):
        logger.info("Initializing Price Aggregator")
        
    async def start(self):
        if self.is_running:
            return
        logger.info("Starting Price Aggregator")
        self.is_running = True
        asyncio.create_task(self._price_update_loop())
        
    async def stop(self):
        if not self.is_running:
            return
        logger.info("Stopping Price Aggregator")
        self.is_running = False
        
    async def get_price(self, token: str, currency: str = "USD") -> Optional[Decimal]:
        cache_key = f"{token}_{currency}"
        
        if cache_key in self.price_cache:
            cached_price = self.price_cache[cache_key]
            if time.time() - cached_price["timestamp"] < 10:
                return Decimal(str(cached_price["price"]))
        
        price = await self._fetch_price(token, currency)
        
        if price:
            self.price_cache[cache_key] = {
                "price": float(price),
                "timestamp": time.time()
            }
        
        return price
    
    async def health_check(self) -> bool:
        return self.is_running and len(self.price_cache) > 0
    
    async def _price_update_loop(self):
        while self.is_running:
            try:
                await self._update_major_token_prices()
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Price update error: {e}")
                await asyncio.sleep(10)
    
    async def _update_major_token_prices(self):
        major_tokens = ["ETH", "BTC", "USDC", "USDT", "DAI"]
        
        for token in major_tokens:
            price = await self._fetch_price(token, "USD")
            if price:
                self.price_cache[f"{token}_USD"] = {
                    "price": float(price),
                    "timestamp": time.time()
                }
    
    async def _fetch_price(self, token: str, currency: str) -> Optional[Decimal]:
        price_map = {
            "ETH_USD": Decimal("2000"),
            "BTC_USD": Decimal("35000"),
            "USDC_USD": Decimal("1.00"),
            "USDT_USD": Decimal("1.00"),
            "DAI_USD": Decimal("1.00")
        }
        
        return price_map.get(f"{token}_{currency}")
