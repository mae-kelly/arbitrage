#!/bin/bash
echo "🎯 Adding Advanced Trading Strategies"

mkdir -p strategies/
mkdir -p risk_management/

# Create advanced strategies
cat > src/advanced_strategies.rs << 'STRATEOF'
// ADVANCED ARBITRAGE STRATEGIES

use std::collections::HashMap;
use crate::ultra_core::UltraOpportunity;

pub trait ArbitrageStrategy {
    fn evaluate_opportunity(&self, opp: &UltraOpportunity) -> f32;
    fn calculate_position_size(&self, opp: &UltraOpportunity, capital: f32) -> f32;
    fn get_risk_score(&self, opp: &UltraOpportunity) -> f32;
}

// Multi-leg arbitrage (triangular, cross-exchange)
pub struct MultiLegStrategy {
    max_legs: usize,
    min_profit_per_leg: f32,
}

impl ArbitrageStrategy for MultiLegStrategy {
    fn evaluate_opportunity(&self, opp: &UltraOpportunity) -> f32 {
        // Complex multi-hop arbitrage evaluation
        opp.profit_bps as f32 * 1.5 // Boost for complexity
    }
    
    fn calculate_position_size(&self, opp: &UltraOpportunity, capital: f32) -> f32 {
        capital * 0.05 // Conservative 5% for complex strategies
    }
    
    fn get_risk_score(&self, opp: &UltraOpportunity) -> f32 {
        0.7 // Higher risk for multi-leg
    }
}

// Statistical arbitrage using mean reversion
pub struct StatisticalArbitrageStrategy {
    lookback_period: usize,
    z_score_threshold: f32,
}

// Momentum-based arbitrage
pub struct MomentumStrategy {
    momentum_window: usize,
    min_momentum: f32,
}

// Market making arbitrage
pub struct MarketMakingStrategy {
    spread_target: f32,
    inventory_limit: f32,
}

// Cross-chain arbitrage
pub struct CrossChainStrategy {
    supported_chains: Vec<String>,
    bridge_costs: HashMap<String, f32>,
}

// MEV-protected arbitrage
pub struct MEVProtectedStrategy {
    private_mempool: bool,
    flashbots_enabled: bool,
}

pub struct StrategyManager {
    strategies: Vec<Box<dyn ArbitrageStrategy>>,
    performance_tracker: HashMap<String, f32>,
}

impl StrategyManager {
    pub fn new() -> Self {
        let mut strategies: Vec<Box<dyn ArbitrageStrategy>> = Vec::new();
        
        strategies.push(Box::new(MultiLegStrategy {
            max_legs: 3,
            min_profit_per_leg: 0.01,
        }));
        
        strategies.push(Box::new(StatisticalArbitrageStrategy {
            lookback_period: 100,
            z_score_threshold: 2.0,
        }));
        
        Self {
            strategies,
            performance_tracker: HashMap::new(),
        }
    }
    
    pub fn evaluate_all_strategies(&self, opp: &UltraOpportunity) -> Vec<(String, f32)> {
        let mut evaluations = Vec::new();
        
        for (i, strategy) in self.strategies.iter().enumerate() {
            let score = strategy.evaluate_opportunity(opp);
            evaluations.push((format!("Strategy_{}", i), score));
        }
        
        evaluations.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        evaluations
    }
}
STRATEOF

echo "✅ Advanced strategies created"

# Create risk management system
cat > src/risk_management.rs << 'RISKEOF'
// ADVANCED RISK MANAGEMENT SYSTEM

use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;

#[derive(Debug, Clone)]
pub struct RiskLimits {
    pub max_position_size: f32,
    pub max_daily_loss: f32,
    pub max_correlation_exposure: f32,
    pub max_exchange_exposure: f32,
    pub max_leverage: f32,
    pub stop_loss_threshold: f32,
}

#[derive(Debug, Clone)]
pub struct RiskMetrics {
    pub var_95: f32,        // Value at Risk (95% confidence)
    pub expected_shortfall: f32,
    pub sharpe_ratio: f32,
    pub max_drawdown: f32,
    pub correlation_risk: f32,
    pub liquidity_risk: f32,
}

pub struct RiskManager {
    limits: Arc<RwLock<RiskLimits>>,
    current_positions: Arc<RwLock<HashMap<String, f32>>>,
    historical_returns: Arc<RwLock<Vec<f32>>>,
    correlation_matrix: Arc<RwLock<HashMap<String, HashMap<String, f32>>>>,
}

impl RiskManager {
    pub fn new() -> Self {
        let limits = RiskLimits {
            max_position_size: 50000.0,    // $50k max position
            max_daily_loss: 5000.0,        // $5k max daily loss
            max_correlation_exposure: 0.3,  // 30% max correlated exposure
            max_exchange_exposure: 0.4,     // 40% max per exchange
            max_leverage: 3.0,              // 3x max leverage
            stop_loss_threshold: 0.02,      // 2% stop loss
        };
        
        Self {
            limits: Arc::new(RwLock::new(limits)),
            current_positions: Arc::new(RwLock::new(HashMap::new())),
            historical_returns: Arc::new(RwLock::new(Vec::new())),
            correlation_matrix: Arc::new(RwLock::new(HashMap::new())),
        }
    }
    
    pub fn check_risk_limits(&self, symbol: &str, position_size: f32) -> Result<(), String> {
        let limits = self.limits.read();
        let positions = self.current_positions.read();
        
        // Position size check
        if position_size > limits.max_position_size {
            return Err(format!("Position size {} exceeds limit {}", 
                             position_size, limits.max_position_size));
        }
        
        // Exchange exposure check
        let exchange_exposure = self.calculate_exchange_exposure(&positions);
        for (exchange, exposure) in exchange_exposure {
            if exposure > limits.max_exchange_exposure {
                return Err(format!("Exchange {} exposure {:.1}% exceeds limit {:.1}%",
                                 exchange, exposure * 100.0, limits.max_exchange_exposure * 100.0));
            }
        }
        
        // Correlation risk check
        let correlation_risk = self.calculate_correlation_risk(symbol, position_size);
        if correlation_risk > limits.max_correlation_exposure {
            return Err(format!("Correlation risk {:.1}% exceeds limit {:.1}%",
                             correlation_risk * 100.0, limits.max_correlation_exposure * 100.0));
        }
        
        Ok(())
    }
    
    pub fn calculate_var_95(&self) -> f32 {
        let returns = self.historical_returns.read();
        if returns.len() < 20 {
            return 0.05; // Default 5% VaR
        }
        
        let mut sorted_returns = returns.clone();
        sorted_returns.sort_by(|a, b| a.partial_cmp(b).unwrap());
        
        let var_index = (returns.len() as f32 * 0.05) as usize;
        sorted_returns[var_index].abs()
    }
    
    pub fn calculate_expected_shortfall(&self) -> f32 {
        let returns = self.historical_returns.read();
        if returns.len() < 20 {
            return 0.07; // Default 7% ES
        }
        
        let var_95 = self.calculate_var_95();
        let tail_losses: Vec<f32> = returns.iter()
            .filter(|&&r| r < -var_95)
            .cloned()
            .collect();
        
        if tail_losses.is_empty() {
            var_95 * 1.4
        } else {
            tail_losses.iter().sum::<f32>() / tail_losses.len() as f32
        }.abs()
    }
    
    fn calculate_exchange_exposure(&self, positions: &HashMap<String, f32>) -> HashMap<String, f32> {
        // Calculate exposure per exchange
        let mut exposure = HashMap::new();
        let total_capital = 100000.0; // Portfolio size
        
        for (symbol, position) in positions {
            let exchange = self.get_exchange_for_symbol(symbol);
            *exposure.entry(exchange).or_insert(0.0) += position / total_capital;
        }
        
        exposure
    }
    
    fn calculate_correlation_risk(&self, symbol: &str, position_size: f32) -> f32 {
        let correlations = self.correlation_matrix.read();
        let positions = self.current_positions.read();
        
        let mut correlation_risk = 0.0;
        
        if let Some(symbol_correls) = correlations.get(symbol) {
            for (other_symbol, correlation) in symbol_correls {
                if let Some(other_position) = positions.get(other_symbol) {
                    correlation_risk += correlation.abs() * other_position * position_size / 100000.0;
                }
            }
        }
        
        correlation_risk
    }
    
    fn get_exchange_for_symbol(&self, symbol: &str) -> String {
        // Extract exchange from symbol (simplified)
        if symbol.contains("binance") { "binance".to_string() }
        else if symbol.contains("coinbase") { "coinbase".to_string() }
        else if symbol.contains("kraken") { "kraken".to_string() }
        else { "unknown".to_string() }
    }
    
    pub fn update_position(&self, symbol: String, position_size: f32) {
        self.current_positions.write().insert(symbol, position_size);
    }
    
    pub fn record_return(&self, return_pct: f32) {
        let mut returns = self.historical_returns.write();
        returns.push(return_pct);
        
        // Keep only last 1000 returns
        if returns.len() > 1000 {
            returns.drain(0..returns.len() - 1000);
        }
    }
    
    pub fn get_risk_metrics(&self) -> RiskMetrics {
        RiskMetrics {
            var_95: self.calculate_var_95(),
            expected_shortfall: self.calculate_expected_shortfall(),
            sharpe_ratio: self.calculate_sharpe_ratio(),
            max_drawdown: self.calculate_max_drawdown(),
            correlation_risk: 0.15, // Placeholder
            liquidity_risk: 0.10,   // Placeholder
        }
    }
    
    fn calculate_sharpe_ratio(&self) -> f32 {
        let returns = self.historical_returns.read();
        if returns.len() < 10 {
            return 0.0;
        }
        
        let mean_return = returns.iter().sum::<f32>() / returns.len() as f32;
        let variance = returns.iter()
            .map(|r| (r - mean_return).powi(2))
            .sum::<f32>() / returns.len() as f32;
        let std_dev = variance.sqrt();
        
        if std_dev == 0.0 { 0.0 } else { mean_return / std_dev }
    }
    
    fn calculate_max_drawdown(&self) -> f32 {
        let returns = self.historical_returns.read();
        if returns.len() < 2 {
            return 0.0;
        }
        
        let mut cumulative = 1.0;
        let mut peak = 1.0;
        let mut max_drawdown = 0.0;
        
        for &return_pct in returns.iter() {
            cumulative *= 1.0 + return_pct;
            if cumulative > peak {
                peak = cumulative;
            }
            let drawdown = (peak - cumulative) / peak;
            if drawdown > max_drawdown {
                max_drawdown = drawdown;
            }
        }
        
        max_drawdown
    }
}

// Global risk manager
lazy_static::lazy_static! {
    pub static ref RISK_MANAGER: Arc<RiskManager> = Arc::new(RiskManager::new());
}
RISKEOF

echo "✅ Advanced risk management created"
