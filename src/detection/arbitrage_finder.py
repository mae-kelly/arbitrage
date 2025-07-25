"""Arbitrage opportunity detection"""
import asyncio
from typing import List, Optional
from loguru import logger
from ..types import ArbitrageOpportunity, OrderBook
from ..data.exchange_manager import ExchangeManager

class ArbitrageFinder:
    def __init__(self, exchange_manager: ExchangeManager, min_profit_percentage: float = 0.5):
        self.exchange_manager = exchange_manager
        self.min_profit_percentage = min_profit_percentage
        
    async def find_opportunities(self, symbol: str) -> List[ArbitrageOpportunity]:
        """Find arbitrage opportunities for a symbol across exchanges"""
        opportunities = []
        
        # Get orderbooks from all exchanges
        orderbooks = {}
        for exchange_name in self.exchange_manager.exchanges.keys():
            orderbook = await self.exchange_manager.get_orderbook(exchange_name, symbol)
            if orderbook and orderbook.bids and orderbook.asks:
                orderbooks[exchange_name] = orderbook
        
        # Find arbitrage opportunities
        for buy_exchange, buy_orderbook in orderbooks.items():
            for sell_exchange, sell_orderbook in orderbooks.items():
                if buy_exchange == sell_exchange:
                    continue
                
                opportunity = self._calculate_arbitrage(
                    symbol, buy_exchange, buy_orderbook, sell_exchange, sell_orderbook
                )
                
                if opportunity and opportunity.profit_percentage >= self.min_profit_percentage:
                    opportunities.append(opportunity)
        
        return opportunities
    
    def _calculate_arbitrage(self, symbol: str, buy_exchange: str, buy_orderbook: OrderBook, 
                           sell_exchange: str, sell_orderbook: OrderBook) -> Optional[ArbitrageOpportunity]:
        """Calculate arbitrage opportunity between two exchanges"""
        try:
            # Best ask price (buy price) from buy exchange
            buy_price = buy_orderbook.asks[0].price
            buy_volume = buy_orderbook.asks[0].volume
            
            # Best bid price (sell price) from sell exchange  
            sell_price = sell_orderbook.bids[0].price
            sell_volume = sell_orderbook.bids[0].volume
            
            # Calculate profit
            if sell_price > buy_price:
                profit_percentage = ((sell_price - buy_price) / buy_price) * 100
                volume = min(buy_volume, sell_volume, 1.0)  # Limit volume for safety
                
                return ArbitrageOpportunity(
                    symbol=symbol,
                    buy_exchange=buy_exchange,
                    sell_exchange=sell_exchange,
                    buy_price=buy_price,
                    sell_price=sell_price,
                    profit_percentage=profit_percentage,
                    volume=volume,
                    timestamp=int(asyncio.get_event_loop().time())
                )
        except Exception as e:
            logger.error(f"Error calculating arbitrage: {e}")
        
        return None
