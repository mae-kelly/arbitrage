"""Smart order routing for optimal execution"""
import asyncio
from typing import Dict, List, Tuple, Optional
from decimal import Decimal
from dataclasses import dataclass
from loguru import logger
import numpy as np

@dataclass
class OrderSlice:
    exchange: str
    symbol: str
    side: str  # 'buy' or 'sell'
    amount: Decimal
    price: Decimal
    expected_fill_time: float
    estimated_cost: Decimal

@dataclass
class ExecutionPlan:
    total_amount: Decimal
    slices: List[OrderSlice]
    total_cost: Decimal
    estimated_slippage: Decimal
    execution_time_estimate: float
    risk_score: float

class SmartOrderRouter:
    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager
        self.execution_history = {}
        self.exchange_performance = {}
        
    async def create_execution_plan(self, symbol: str, side: str, 
                                  total_amount: Decimal, 
                                  max_slippage: Decimal = Decimal('0.01')) -> ExecutionPlan:
        """Create optimal execution plan across exchanges"""
        
        # Get orderbooks from all healthy exchanges
        orderbooks = await self.exchange_manager.get_all_orderbooks(symbol)
        
        if not orderbooks:
            raise Exception(f"No orderbooks available for {symbol}")
        
        # Analyze liquidity across exchanges
        liquidity_analysis = await self._analyze_liquidity(orderbooks, side)
        
        # Create order slices
        slices = await self._optimize_order_slicing(
            symbol, side, total_amount, liquidity_analysis, max_slippage
        )
        
        # Calculate execution metrics
        total_cost = sum(slice.estimated_cost for slice in slices)
        estimated_slippage = await self._calculate_slippage(slices, orderbooks, side)
        execution_time = max(slice.expected_fill_time for slice in slices)
        risk_score = await self._calculate_execution_risk(slices)
        
        return ExecutionPlan(
            total_amount=total_amount,
            slices=slices,
            total_cost=total_cost,
            estimated_slippage=estimated_slippage,
            execution_time_estimate=execution_time,
            risk_score=risk_score
        )
    
    async def _analyze_liquidity(self, orderbooks: Dict, side: str) -> Dict:
        """Analyze available liquidity across exchanges"""
        liquidity_data = {}
        
        for exchange, orderbook in orderbooks.items():
            try:
                levels = orderbook['asks'] if side == 'buy' else orderbook['bids']
                
                if not levels:
                    continue
                
                # Calculate depth at different price levels
                cumulative_volume = Decimal('0')
                price_levels = []
                
                for price, volume in levels[:10]:  # Top 10 levels
                    cumulative_volume += Decimal(str(volume))
                    price_levels.append({
                        'price': Decimal(str(price)),
                        'volume': Decimal(str(volume)),
                        'cumulative_volume': cumulative_volume
                    })
                
                # Calculate liquidity metrics
                total_volume = cumulative_volume
                avg_price = sum(level['price'] * level['volume'] for level in price_levels) / total_volume if total_volume > 0 else Decimal('0')
                
                # Factor in exchange performance
                latency = self.exchange_manager.latencies.get(exchange, 100)
                health = self.exchange_manager.connection_health.get(exchange, False)
                
                liquidity_data[exchange] = {
                    'price_levels': price_levels,
                    'total_volume': total_volume,
                    'avg_price': avg_price,
                    'latency': latency,
                    'health_score': 1.0 if health else 0.0,
                    'execution_score': self._calculate_execution_score(exchange, latency, total_volume)
                }
                
            except Exception as e:
                logger.error(f"Liquidity analysis failed for {exchange}: {e}")
        
        return liquidity_data
    
    def _calculate_execution_score(self, exchange: str, latency: float, volume: Decimal) -> float:
        """Calculate execution score for exchange"""
        base_score = 0.5
        
        # Tier bonus
        if exchange in self.exchange_manager.tier1_exchanges:
            tier_bonus = 0.3
        elif exchange in self.exchange_manager.tier2_exchanges:
            tier_bonus = 0.2
        else:
            tier_bonus = 0.1
        
        # Latency penalty
        latency_penalty = min(latency / 1000.0, 0.2)  # Max 0.2 penalty
        
        # Volume bonus
        volume_bonus = min(float(volume) / 100.0, 0.2)  # Max 0.2 bonus
        
        return min(base_score + tier_bonus + volume_bonus - latency_penalty, 1.0)
    
    async def _optimize_order_slicing(self, symbol: str, side: str, total_amount: Decimal,
                                    liquidity_analysis: Dict, max_slippage: Decimal) -> List[OrderSlice]:
        """Optimize order slicing across exchanges"""
        slices = []
        remaining_amount = total_amount
        
        # Sort exchanges by execution score
        sorted_exchanges = sorted(
            liquidity_analysis.items(),
            key=lambda x: x[1]['execution_score'],
            reverse=True
        )
        
        for exchange, data in sorted_exchanges:
            if remaining_amount <= 0:
                break
            
            if data['total_volume'] <= 0:
                continue
            
            # Calculate optimal slice size for this exchange
            max_slice_size = min(
                remaining_amount,
                data['total_volume'] * Decimal('0.8'),  # Use max 80% of available liquidity
                total_amount * Decimal('0.4')  # Max 40% on any single exchange
            )
            
            if max_slice_size > Decimal('0.01'):  # Minimum viable slice
                best_price = data['price_levels'][0]['price']
                
                slice = OrderSlice(
                    exchange=exchange,
                    symbol=symbol,
                    side=side,
                    amount=max_slice_size,
                    price=best_price,
                    expected_fill_time=data['latency'] / 1000.0,
                    estimated_cost=max_slice_size * best_price
                )
                
                slices.append(slice)
                remaining_amount -= max_slice_size
        
        if remaining_amount > Decimal('0.01'):
            logger.warning(f"Could not route full amount. Remaining: {remaining_amount}")
        
        return slices
    
    async def _calculate_slippage(self, slices: List[OrderSlice], orderbooks: Dict, side: str) -> Decimal:
        """Calculate estimated slippage for execution plan"""
        total_slippage = Decimal('0')
        
        for slice in slices:
            try:
                orderbook = orderbooks[slice.exchange]
                levels = orderbook['asks'] if side == 'buy' else orderbook['bids']
                
                if levels:
                    mid_price = Decimal(str(levels[0][0]))
                    execution_price = slice.price
                    
                    slice_slippage = abs(execution_price - mid_price) / mid_price
                    weight = slice.amount / sum(s.amount for s in slices)
                    
                    total_slippage += slice_slippage * weight
                    
            except Exception as e:
                logger.error(f"Slippage calculation failed for {slice.exchange}: {e}")
        
        return total_slippage
    
    async def _calculate_execution_risk(self, slices: List[OrderSlice]) -> float:
        """Calculate overall execution risk"""
        if not slices:
            return 1.0
        
        # Risk factors
        exchange_concentration = len(slices) / 10.0  # More exchanges = lower risk
        avg_execution_time = sum(slice.expected_fill_time for slice in slices) / len(slices)
        time_risk = min(avg_execution_time / 5.0, 1.0)  # Higher time = higher risk
        
        # Exchange tier risk
        tier1_weight = sum(slice.amount for slice in slices 
                          if slice.exchange in self.exchange_manager.tier1_exchanges)
        total_weight = sum(slice.amount for slice in slices)
        tier_risk = 1.0 - (tier1_weight / total_weight if total_weight > 0 else 0)
        
        # Composite risk (0 = low risk, 1 = high risk)
        risk_score = (exchange_concentration * 0.3 + time_risk * 0.4 + tier_risk * 0.3)
        return min(risk_score, 1.0)
