"""Kelly Criterion position sizing for optimal capital allocation"""
import numpy as np
from typing import Dict, List, Tuple, Optional
from decimal import Decimal
import asyncio
from loguru import logger

class KellyOptimizer:
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.historical_trades = []
        self.win_rate_cache = {}
        self.volatility_cache = {}
        
    async def calculate_optimal_position_size(self, 
                                            opportunity_type: str,
                                            expected_profit: Decimal,
                                            estimated_risk: float,
                                            current_capital: Decimal,
                                            max_position_pct: float = 0.02) -> Decimal:
        """Calculate optimal position size using Kelly Criterion"""
        
        # Get historical performance for this strategy
        win_rate, avg_win, avg_loss = await self._get_strategy_statistics(opportunity_type)
        
        if win_rate is None or avg_win is None or avg_loss is None:
            # Default conservative sizing for new strategies
            return current_capital * Decimal(str(max_position_pct * 0.5))
        
        # Calculate Kelly fraction
        kelly_fraction = self._calculate_kelly_fraction(win_rate, avg_win, avg_loss)
        
        # Apply risk adjustments
        risk_adjusted_fraction = self._apply_risk_adjustments(
            kelly_fraction, estimated_risk, opportunity_type
        )
        
        # Apply maximum position limit
        final_fraction = min(risk_adjusted_fraction, max_position_pct)
        
        position_size = current_capital * Decimal(str(final_fraction))
        
        logger.info(f"Kelly sizing for {opportunity_type}: "
                   f"raw={kelly_fraction:.4f}, "
                   f"risk_adj={risk_adjusted_fraction:.4f}, "
                   f"final={final_fraction:.4f}")
        
        return position_size
    
    def _calculate_kelly_fraction(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """Calculate raw Kelly fraction"""
        if avg_loss <= 0:
            return 0.0
        
        # Kelly formula: f = (bp - q) / b
        # where b = avg_win/avg_loss, p = win_rate, q = 1 - win_rate
        b = avg_win / avg_loss
        p = win_rate
        q = 1 - win_rate
        
        kelly_fraction = (b * p - q) / b
        
        # Ensure non-negative
        return max(0.0, kelly_fraction)
    
    def _apply_risk_adjustments(self, kelly_fraction: float, estimated_risk: float, 
                              strategy_type: str) -> float:
        """Apply various risk adjustments to Kelly fraction"""
        
        # Base risk adjustment (reduce Kelly by risk score)
        risk_adjustment = 1.0 - (estimated_risk * 0.5)
        
        # Strategy-specific adjustments
        strategy_adjustments = {
            'spatial': 0.8,      # Conservative for execution risk
            'triangular': 0.7,   # More conservative due to complexity
            'cross_chain': 0.6,  # Most conservative due to bridge risks
            'funding_rate': 0.9, # Less conservative for funding arbitrage
            'statistical': 0.5   # Very conservative for statistical strategies
        }
        
        strategy_factor = strategy_adjustments.get(strategy_type, 0.7)
        
        # Volatility adjustment (reduce during high volatility periods)
        volatility_factor = await self._get_volatility_adjustment()
        
        # Composite adjustment
        adjusted_fraction = (kelly_fraction * risk_adjustment * 
                           strategy_factor * volatility_factor)
        
        return max(0.0, min(adjusted_fraction, 0.25))  # Cap at 25%
    
    async def _get_strategy_statistics(self, strategy_type: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Get win rate and average win/loss for strategy"""
        try:
            if self.redis_client:
                # Try to get from Redis cache
                stats_key = f"strategy_stats:{strategy_type}"
                stats_data = await self.redis_client.hgetall(stats_key)
                
                if stats_data:
                    return (
                        float(stats_data.get('win_rate', 0)),
                        float(stats_data.get('avg_win', 0)),
                        float(stats_data.get('avg_loss', 0))
                    )
            
            # Calculate from historical trades
            strategy_trades = [trade for trade in self.historical_trades 
                             if trade.get('strategy_type') == strategy_type]
            
            if len(strategy_trades) < 10:  # Need at least 10 trades
                return None, None, None
            
            wins = [trade['profit'] for trade in strategy_trades if trade['profit'] > 0]
            losses = [-trade['profit'] for trade in strategy_trades if trade['profit'] < 0]
            
            if not wins or not losses:
                return None, None, None
            
            win_rate = len(wins) / len(strategy_trades)
            avg_win = sum(wins) / len(wins)
            avg_loss = sum(losses) / len(losses)
            
            # Cache results
            if self.redis_client:
                await self.redis_client.hset(stats_key, mapping={
                    'win_rate': win_rate,
                    'avg_win': avg_win,
                    'avg_loss': avg_loss
                })
                await self.redis_client.expire(stats_key, 3600)  # 1 hour cache
            
            return win_rate, avg_win, avg_loss
            
        except Exception as e:
            logger.error(f"Error getting strategy statistics: {e}")
            return None, None, None
    
    async def _get_volatility_adjustment(self) -> float:
        """Get market volatility adjustment factor"""
        try:
            # Simple volatility measure based on recent price movements
            # In production, this would use more sophisticated volatility models
            base_volatility_factor = 0.9
            
            # Could integrate with VIX, realized volatility, etc.
            # For now, return base factor
            return base_volatility_factor
            
        except Exception as e:
            logger.error(f"Error calculating volatility adjustment: {e}")
            return 0.8  # Conservative default
    
    async def update_trade_result(self, strategy_type: str, profit: float, 
                                capital_used: float):
        """Update historical trade data for strategy learning"""
        trade_record = {
            'strategy_type': strategy_type,
            'profit': profit,
            'capital_used': capital_used,
            'timestamp': asyncio.get_event_loop().time(),
            'return_pct': profit / capital_used if capital_used > 0 else 0
        }
        
        self.historical_trades.append(trade_record)
        
        # Keep only recent trades (last 1000)
        if len(self.historical_trades) > 1000:
            self.historical_trades = self.historical_trades[-1000:]
        
        # Invalidate cache for this strategy
        if self.redis_client:
            stats_key = f"strategy_stats:{strategy_type}"
            await self.redis_client.delete(stats_key)
    
    async def get_portfolio_allocation(self, opportunities: List[Dict], 
                                     total_capital: Decimal) -> Dict[str, Decimal]:
        """Calculate optimal portfolio allocation across multiple opportunities"""
        if not opportunities:
            return {}
        
        allocations = {}
        remaining_capital = total_capital
        
        # Sort opportunities by expected Sharpe ratio
        sorted_opps = sorted(
            opportunities,
            key=lambda x: x.get('expected_profit', 0) / max(x.get('risk_score', 1), 0.1),
            reverse=True
        )
        
        for opp in sorted_opps:
            if remaining_capital <= 0:
                break
            
            position_size = await self.calculate_optimal_position_size(
                opp['strategy_type'],
                opp['expected_profit'],
                opp['risk_score'],
                remaining_capital
            )
            
            if position_size > 0:
                allocations[opp['id']] = position_size
                remaining_capital -= position_size
        
        return allocations
