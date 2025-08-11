import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio

@dataclass
class RiskMetrics:
    var_95: float
    var_99: float
    expected_shortfall: float
    max_drawdown: float
    sharpe_ratio: float
    correlation_risk: float

@dataclass
class PositionRisk:
    asset: str
    position_size: float
    notional_value: float
    var_contribution: float
    concentration_risk: float

class RiskManager:
    def __init__(self, config: Dict):
        self.config = config
        self.max_portfolio_risk = config.get('max_portfolio_risk', 0.02)
        self.max_single_position = config.get('max_single_position', 0.1)
        self.max_correlation = config.get('max_correlation', 0.7)
        self.lookback_period = config.get('lookback_period', 252)
        self.confidence_levels = [0.95, 0.99]
        
        self.portfolio_value = 1000000
        self.positions = {}
        self.price_history = {}
        self.returns_history = {}
        self.risk_metrics_cache = None
        self.last_risk_calculation = None
        
    def add_position(self, asset: str, quantity: float, price: float):
        self.positions[asset] = {
            'quantity': quantity,
            'price': price,
            'notional': abs(quantity * price),
            'timestamp': datetime.now()
        }
        
    def remove_position(self, asset: str):
        if asset in self.positions:
            del self.positions[asset]
    
    def update_price_history(self, asset: str, price: float, timestamp: datetime = None):
        if timestamp is None:
            timestamp = datetime.now()
            
        if asset not in self.price_history:
            self.price_history[asset] = []
            
        self.price_history[asset].append((timestamp, price))
        
        if len(self.price_history[asset]) > self.lookback_period:
            self.price_history[asset] = self.price_history[asset][-self.lookback_period:]
            
        self._update_returns_history(asset)
    
    def _update_returns_history(self, asset: str):
        if asset not in self.price_history or len(self.price_history[asset]) < 2:
            return
            
        prices = [p[1] for p in self.price_history[asset]]
        returns = np.diff(np.log(prices))
        
        self.returns_history[asset] = returns.tolist()
    
    async def calculate_position_size(self, asset: str, signal_strength: float, current_price: float) -> float:
        if not self._has_sufficient_data(asset):
            return self._get_conservative_position_size(current_price)
        
        asset_volatility = self._calculate_volatility(asset)
        kelly_fraction = self._calculate_kelly_fraction(asset, signal_strength)
        
        risk_adjusted_kelly = min(kelly_fraction * 0.25, self.max_single_position)
        
        correlation_adjustment = self._calculate_correlation_adjustment(asset)
        liquidity_adjustment = self._calculate_liquidity_adjustment(asset)
        
        final_fraction = risk_adjusted_kelly * correlation_adjustment * liquidity_adjustment
        
        max_notional = self.portfolio_value * final_fraction
        max_quantity = max_notional / current_price
        
        return max_quantity
    
    def _calculate_kelly_fraction(self, asset: str, signal_strength: float) -> float:
        if asset not in self.returns_history or len(self.returns_history[asset]) < 30:
            return 0.01
        
        returns = np.array(self.returns_history[asset])
        
        win_probability = np.sum(returns > 0) / len(returns)
        
        if win_probability == 0:
            return 0.0
        
        avg_win = np.mean(returns[returns > 0]) if np.any(returns > 0) else 0
        avg_loss = np.mean(returns[returns < 0]) if np.any(returns < 0) else 0
        
        if avg_loss == 0:
            return min(0.1, signal_strength * 0.05)
        
        win_loss_ratio = abs(avg_win / avg_loss)
        
        kelly_fraction = win_probability - (1 - win_probability) / win_loss_ratio
        
        return max(0, min(kelly_fraction * signal_strength, 0.25))
    
    def _calculate_correlation_adjustment(self, asset: str) -> float:
        if len(self.positions) < 2:
            return 1.0
        
        total_correlation = 0
        correlation_count = 0
        
        for existing_asset in self.positions.keys():
            if existing_asset != asset and self._has_sufficient_data(existing_asset):
                correlation = self._calculate_correlation(asset, existing_asset)
                total_correlation += abs(correlation)
                correlation_count += 1
        
        if correlation_count == 0:
            return 1.0
        
        avg_correlation = total_correlation / correlation_count
        
        if avg_correlation > self.max_correlation:
            return max(0.1, 1.0 - (avg_correlation - self.max_correlation) * 2)
        
        return 1.0
    
    def _calculate_correlation(self, asset1: str, asset2: str) -> float:
        if (asset1 not in self.returns_history or asset2 not in self.returns_history or
            len(self.returns_history[asset1]) < 30 or len(self.returns_history[asset2]) < 30):
            return 0.0
        
        returns1 = np.array(self.returns_history[asset1][-30:])
        returns2 = np.array(self.returns_history[asset2][-30:])
        
        min_length = min(len(returns1), len(returns2))
        returns1 = returns1[-min_length:]
        returns2 = returns2[-min_length:]
        
        if np.std(returns1) == 0 or np.std(returns2) == 0:
            return 0.0
        
        correlation = np.corrcoef(returns1, returns2)[0, 1]
        return correlation if not np.isnan(correlation) else 0.0
    
    def _calculate_liquidity_adjustment(self, asset: str) -> float:
        return 1.0
    
    def _calculate_volatility(self, asset: str) -> float:
        if asset not in self.returns_history or len(self.returns_history[asset]) < 10:
            return 0.02
        
        returns = np.array(self.returns_history[asset])
        return np.std(returns) * np.sqrt(252)
    
    async def calculate_portfolio_risk(self) -> RiskMetrics:
        if (self.risk_metrics_cache and self.last_risk_calculation and 
            datetime.now() - self.last_risk_calculation < timedelta(minutes=5)):
            return self.risk_metrics_cache
        
        portfolio_returns = self._calculate_portfolio_returns()
        
        if len(portfolio_returns) < 30:
            return RiskMetrics(0.01, 0.02, 0.025, 0.05, 0.0, 0.0)
        
        returns_array = np.array(portfolio_returns)
        
        var_95 = np.percentile(returns_array, 5)
        var_99 = np.percentile(returns_array, 1)
        
        expected_shortfall = np.mean(returns_array[returns_array <= var_95])
        
        cumulative_returns = np.cumprod(1 + returns_array)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = np.min(drawdowns)
        
        sharpe_ratio = np.mean(returns_array) / np.std(returns_array) * np.sqrt(252) if np.std(returns_array) > 0 else 0
        
        correlation_risk = self._calculate_portfolio_correlation_risk()
        
        self.risk_metrics_cache = RiskMetrics(
            var_95=abs(var_95),
            var_99=abs(var_99),
            expected_shortfall=abs(expected_shortfall),
            max_drawdown=abs(max_drawdown),
            sharpe_ratio=sharpe_ratio,
            correlation_risk=correlation_risk
        )
        
        self.last_risk_calculation = datetime.now()
        return self.risk_metrics_cache
    
    def _calculate_portfolio_returns(self) -> List[float]:
        if not self.positions:
            return []
        
        portfolio_returns = []
        
        min_length = min(len(self.returns_history.get(asset, [])) for asset in self.positions.keys() 
                        if asset in self.returns_history)
        
        if min_length < 2:
            return []
        
        for i in range(min_length):
            total_return = 0
            total_weight = 0
            
            for asset, position in self.positions.items():
                if asset in self.returns_history and len(self.returns_history[asset]) > i:
                    weight = position['notional'] / sum(p['notional'] for p in self.positions.values())
                    asset_return = self.returns_history[asset][-(i+1)]
                    total_return += weight * asset_return
                    total_weight += weight
            
            if total_weight > 0:
                portfolio_returns.append(total_return)
        
        return portfolio_returns[::-1]
    
    def _calculate_portfolio_correlation_risk(self) -> float:
        if len(self.positions) < 2:
            return 0.0
        
        assets = list(self.positions.keys())
        correlations = []
        
        for i in range(len(assets)):
            for j in range(i + 1, len(assets)):
                correlation = self._calculate_correlation(assets[i], assets[j])
                correlations.append(abs(correlation))
        
        return np.mean(correlations) if correlations else 0.0
    
    def _has_sufficient_data(self, asset: str) -> bool:
        return (asset in self.returns_history and 
                len(self.returns_history[asset]) >= 10)
    
    def _get_conservative_position_size(self, current_price: float) -> float:
        conservative_fraction = 0.001
        max_notional = self.portfolio_value * conservative_fraction
        return max_notional / current_price
    
    async def validate_trade(self, asset: str, quantity: float, price: float) -> bool:
        notional_value = abs(quantity * price)
        
        if notional_value > self.portfolio_value * self.max_single_position:
            return False
        
        temp_positions = self.positions.copy()
        temp_positions[asset] = {
            'quantity': quantity,
            'price': price,
            'notional': notional_value,
            'timestamp': datetime.now()
        }
        
        total_notional = sum(p['notional'] for p in temp_positions.values())
        if total_notional > self.portfolio_value:
            return False
        
        risk_metrics = await self.calculate_portfolio_risk()
        if risk_metrics.var_95 > self.max_portfolio_risk:
            return False
        
        return True
    
    def get_position_limits(self) -> Dict[str, float]:
        return {
            'max_single_position': self.max_single_position,
            'max_portfolio_risk': self.max_portfolio_risk,
            'max_correlation': self.max_correlation,
            'available_capital': self.portfolio_value - sum(p['notional'] for p in self.positions.values())
        }
