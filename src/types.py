"""Core data types for crypto arbitrage system"""
from dataclasses import dataclass
from typing import List, Optional
from decimal import Decimal

@dataclass
class PriceLevel:
    price: float
    volume: float

@dataclass
class OrderBook:
    symbol: str
    bids: List[PriceLevel]
    asks: List[PriceLevel]
    timestamp: int
    exchange: Optional[str] = None

@dataclass
class ArbitrageOpportunity:
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    profit_percentage: float
    volume: float
    timestamp: int
    
    @property
    def profit_amount(self) -> float:
        return (self.sell_price - self.buy_price) * self.volume
