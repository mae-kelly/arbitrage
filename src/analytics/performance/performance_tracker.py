"""Advanced performance tracking and analytics"""
import asyncio
import json
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass, asdict
from loguru import logger

@dataclass
class TradeRecord:
    id: str
    strategy_type: str
    symbol: str
    side: str
    amount: Decimal
    entry_price: Decimal
    exit_price: Decimal
    profit_loss: Decimal
    fees: Decimal
    execution_time: float
    slippage: Decimal
    timestamp: datetime
    exchange: str
    success: bool

@dataclass
class PerformanceMetrics:
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_profit: Decimal
    total_fees: Decimal
    net_profit: Decimal
    avg_profit_per_trade: Decimal
    max_profit: Decimal
    max_loss: Decimal
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: Decimal
    recovery_factor: float
    avg_execution_time: float

class PerformanceTracker:
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.trades: List[TradeRecord] = []
        self.daily_pnl: Dict[str, Decimal] = {}
        self.strategy_performance: Dict[str, List[TradeRecord]] = {}
        
    async def record_trade(self, trade: TradeRecord):
        """Record a completed trade"""
        self.trades.append(trade)
        
        # Update strategy-specific tracking
        if trade.strategy_type not in self.strategy_performance:
            self.strategy_performance[trade.strategy_type] = []
        self.strategy_performance[trade.strategy_type].append(trade)
        
        # Update daily P&L
        date_key = trade.timestamp.strftime('%Y-%m-%d')
        if date_key not in self.daily_pnl:
            self.daily_pnl[date_key] = Decimal('0')
        self.daily_pnl[date_key] += trade.profit_loss
        
        # Store in Redis for persistence
        if self.redis_client:
            await self._store_trade_in_redis(trade)
        
        logger.info(f"Recorded trade: {trade.strategy_type} {trade.symbol} "
                   f"P&L: ${trade.profit_loss:.2f}")
    
    async def _store_trade_in_redis(self, trade: TradeRecord):
        """Store trade record in Redis"""
        try:
            trade_key = f"trade:{trade.id}"
            trade_data = asdict(trade)
            
            # Convert Decimal and datetime to JSON-serializable formats
            for key, value in trade_data.items():
                if isinstance(value, Decimal):
                    trade_data[key] = str(value)
                elif isinstance(value, datetime):
                    trade_data[key] = value.isoformat()
            
            await self.redis_client.set(
                trade_key, 
                json.dumps(trade_data),
                ex=86400 * 30  # Keep for 30 days
            )
            
            # Add to strategy index
            strategy_key = f"strategy_trades:{trade.strategy_type}"
            await self.redis_client.zadd(
                strategy_key,
                {trade.id: trade.timestamp.timestamp()}
            )
            
        except Exception as e:
            logger.error(f"Failed to store trade in Redis: {e}")
    
    async def get_performance_metrics(self, 
                                    strategy_type: Optional[str] = None,
                                    lookback_days: Optional[int] = None) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        
        # Filter trades based on criteria
        filtered_trades = self.trades
        
        if strategy_type:
            filtered_trades = [t for t in filtered_trades if t.strategy_type == strategy_type]
        
        if lookback_days:
            cutoff_date = datetime.now() - timedelta(days=lookback_days)
            filtered_trades = [t for t in filtered_trades if t.timestamp >= cutoff_date]
        
        if not filtered_trades:
            return self._empty_metrics()
        
        # Basic metrics
        total_trades = len(filtered_trades)
        winning_trades = len([t for t in filtered_trades if t.profit_loss > 0])
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # P&L metrics
        total_profit = sum(t.profit_loss for t in filtered_trades)
        total_fees = sum(t.fees for t in filtered_trades)
        net_profit = total_profit - total_fees
        avg_profit_per_trade = net_profit / total_trades if total_trades > 0 else Decimal('0')
        
        # Risk metrics
        profits = [t.profit_loss for t in filtered_trades if t.profit_loss > 0]
        losses = [t.profit_loss for t in filtered_trades if t.profit_loss < 0]
        
        max_profit = max(profits) if profits else Decimal('0')
        max_loss = min(losses) if losses else Decimal('0')
        
        # Profit factor (gross profit / gross loss)
        gross_profit = sum(profits) if profits else Decimal('0')
        gross_loss = abs(sum(losses)) if losses else Decimal('0')
        profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else float('inf')
        
        # Sharpe ratio
        returns = [float(t.profit_loss) for t in filtered_trades]
        sharpe_ratio = self._calculate_sharpe_ratio(returns)
        
        # Drawdown metrics
        max_drawdown = await self._calculate_max_drawdown(filtered_trades)
        recovery_factor = float(net_profit / abs(max_drawdown)) if max_drawdown != 0 else float('inf')
        
        # Execution metrics
        avg_execution_time = sum(t.execution_time for t in filtered_trades) / total_trades
        
        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_profit=total_profit,
            total_fees=total_fees,
            net_profit=net_profit,
            avg_profit_per_trade=avg_profit_per_trade,
            max_profit=max_profit,
            max_loss=max_loss,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            recovery_factor=recovery_factor,
            avg_execution_time=avg_execution_time
        )
    
    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio for the returns"""
        if len(returns) < 2:
            return 0.0
        
        returns_array = np.array(returns)
        excess_returns = returns_array - (risk_free_rate / 252)  # Daily risk-free rate
        
        if np.std(excess_returns) == 0:
            return 0.0
        
        return float(np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252))
    
    async def _calculate_max_drawdown(self, trades: List[TradeRecord]) -> Decimal:
        """Calculate maximum drawdown"""
        if not trades:
            return Decimal('0')
        
        # Calculate cumulative P&L
        cumulative_pnl = []
        running_total = Decimal('0')
        
        for trade in sorted(trades, key=lambda x: x.timestamp):
            running_total += trade.profit_loss
            cumulative_pnl.append(running_total)
        
        # Calculate drawdown
        peak = cumulative_pnl[0]
        max_drawdown = Decimal('0')
        
        for pnl in cumulative_pnl:
            if pnl > peak:
                peak = pnl
            
            drawdown = peak - pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return max_drawdown
    
    def _empty_metrics(self) -> PerformanceMetrics:
        """Return empty metrics object"""
        return PerformanceMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_profit=Decimal('0'),
            total_fees=Decimal('0'),
            net_profit=Decimal('0'),
            avg_profit_per_trade=Decimal('0'),
            max_profit=Decimal('0'),
            max_loss=Decimal('0'),
            profit_factor=0.0,
            sharpe_ratio=0.0,
            max_drawdown=Decimal('0'),
            recovery_factor=0.0,
            avg_execution_time=0.0
        )
    
    async def get_strategy_comparison(self) -> Dict[str, PerformanceMetrics]:
        """Compare performance across strategies"""
        comparison = {}
        
        for strategy_type in self.strategy_performance.keys():
            metrics = await self.get_performance_metrics(strategy_type=strategy_type)
            comparison[strategy_type] = metrics
        
        return comparison
    
    async def get_daily_pnl_chart_data(self, days: int = 30) -> Dict[str, float]:
        """Get daily P&L data for charting"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        chart_data = {}
        current_date = cutoff_date
        
        while current_date <= datetime.now():
            date_key = current_date.strftime('%Y-%m-%d')
            pnl = self.daily_pnl.get(date_key, Decimal('0'))
            chart_data[date_key] = float(pnl)
            current_date += timedelta(days=1)
        
        return chart_data
    
    async def generate_performance_report(self, strategy_type: Optional[str] = None) -> Dict:
        """Generate comprehensive performance report"""
        metrics = await self.get_performance_metrics(strategy_type=strategy_type)
        strategy_comparison = await self.get_strategy_comparison()
        daily_pnl = await self.get_daily_pnl_chart_data()
        
        return {
            'overall_metrics': asdict(metrics),
            'strategy_comparison': {k: asdict(v) for k, v in strategy_comparison.items()},
            'daily_pnl': daily_pnl,
            'generated_at': datetime.now().isoformat()
        }
