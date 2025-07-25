import asyncio
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from loguru import logger
from src.data.exchange_manager import ExchangeManager
from src.types import ArbitrageOpportunity
import uuid

class ArbitrageFinder:
    def __init__(self, exchange_manager: ExchangeManager):
        self.exchange_manager = exchange_manager
        self.min_profit_threshold = Decimal('0.005')  # 0.5%
        self.opportunities = []
        
    async def find_spatial_arbitrage(self, symbol: str) -> List[ArbitrageOpportunity]:
        """Find spatial arbitrage opportunities"""
        orderbooks = await self.exchange_manager.get_all_orderbooks(symbol)
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
                
                # Check if we can buy on A and sell on B
                buy_price = Decimal(str(ob_a['asks'][0][0]))
                sell_price = Decimal(str(ob_b['bids'][0][0]))
                
                if sell_price > buy_price:
                    profit_pct = (sell_price - buy_price) / buy_price
                    
                    if profit_pct > self.min_profit_threshold:
                        opportunity = ArbitrageOpportunity(
                            id=str(uuid.uuid4()),
                            type='spatial',
                            symbol=symbol,
                            buy_exchange=exchange_a,
                            sell_exchange=exchange_b,
                            buy_price=buy_price,
                            sell_price=sell_price,
                            profit_pct=profit_pct,
                            profit_usd=profit_pct * Decimal('1000'),  # Assume $1000 trade
                            confidence=0.8,
                            timestamp=datetime.now(),
                            expires_at=datetime.now() + timedelta(seconds=30)
                        )
                        opportunities.append(opportunity)
                        
                        logger.info(f"Found arbitrage: Buy {symbol} on {exchange_a} "
                                  f"at ${buy_price}, sell on {exchange_b} at ${sell_price} "
                                  f"(profit: {profit_pct:.2%})")
        
        return opportunities
    
    async def monitor_arbitrage(self):
        """Continuously monitor for arbitrage opportunities"""
        while True:
            try:
                all_opportunities = []
                
                for symbol in ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']:
                    spatial_opps = await self.find_spatial_arbitrage(symbol)
                    all_opportunities.extend(spatial_opps)
                
                self.opportunities = all_opportunities
                
                if all_opportunities:
                    logger.info(f"Found {len(all_opportunities)} arbitrage opportunities")
                
            except Exception as e:
                logger.error(f"Error in arbitrage monitoring: {e}")
            
            await asyncio.sleep(2)
    
    def get_best_opportunities(self, limit: int = 5) -> List[ArbitrageOpportunity]:
        """Get the best arbitrage opportunities"""
        valid_opportunities = [
            opp for opp in self.opportunities 
            if opp.expires_at > datetime.now()
        ]
        
        return sorted(
            valid_opportunities, 
            key=lambda x: x.profit_pct, 
            reverse=True
        )[:limit]
