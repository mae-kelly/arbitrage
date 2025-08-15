//! Advanced Production Risk Management System

use anyhow::Result;
use nalgebra::{DMatrix, DVector};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use tokio::sync::RwLock;
use std::sync::Arc;

#[derive(Debug, Clone, Serialize)]
pub struct AdvancedRiskManager {
    position_limits: HashMap<String, PositionLimit>,
    correlation_matrix: Arc<RwLock<DMatrix<f64>>>,
    var_calculator: VaRCalculator,
    stress_scenarios: Vec<StressScenario>,
    circuit_breakers: CircuitBreakers,
}

#[derive(Debug, Clone, Serialize)]
pub struct PositionLimit {
    max_position_usd: f64,
    max_daily_volume_usd: f64,
    max_leverage: f64,
    sector_limit: f64,
}

#[derive(Debug, Clone)]
pub struct VaRCalculator {
    confidence_level: f64,
    time_horizon_days: u32,
    simulation_runs: u32,
}

#[derive(Debug, Clone)]
pub struct StressScenario {
    name: String,
    market_shock_pct: f64,
    correlation_shock: f64,
    liquidity_shock_pct: f64,
}

#[derive(Debug, Clone)]
pub struct CircuitBreakers {
    max_daily_loss_usd: f64,
    max_portfolio_var: f64,
    min_sharpe_ratio: f64,
    emergency_stop: bool,
}

impl AdvancedRiskManager {
    pub fn new() -> Self {
        Self {
            position_limits: Self::default_limits(),
            correlation_matrix: Arc::new(RwLock::new(DMatrix::identity(100, 100))),
            var_calculator: VaRCalculator {
                confidence_level: 0.95,
                time_horizon_days: 1,
                simulation_runs: 10000,
            },
            stress_scenarios: Self::default_stress_scenarios(),
            circuit_breakers: CircuitBreakers {
                max_daily_loss_usd: 10000.0,
                max_portfolio_var: 5000.0,
                min_sharpe_ratio: 0.5,
                emergency_stop: false,
            },
        }
    }

    pub async fn calculate_portfolio_var(&self, positions: &[Position]) -> Result<f64> {
        let correlation_matrix = self.correlation_matrix.read().await;
        
        // Monte Carlo VaR calculation
        let mut losses = Vec::with_capacity(self.var_calculator.simulation_runs as usize);
        
        for _ in 0..self.var_calculator.simulation_runs {
            let portfolio_loss = self.simulate_portfolio_loss(positions, &correlation_matrix);
            losses.push(portfolio_loss);
        }
        
        losses.sort_by(|a, b| b.partial_cmp(a).unwrap());
        let var_index = ((1.0 - self.var_calculator.confidence_level) * losses.len() as f64) as usize;
        
        Ok(losses[var_index])
    }

    fn simulate_portfolio_loss(&self, positions: &[Position], correlation_matrix: &DMatrix<f64>) -> f64 {
        use rand_distr::{Normal, Distribution};
        let mut rng = rand::thread_rng();
        let normal = Normal::new(0.0, 1.0).unwrap();
        
        let mut total_loss = 0.0;
        
        for (i, position) in positions.iter().enumerate() {
            let shock = normal.sample(&mut rng);
            let correlated_shock = self.apply_correlation(shock, i, correlation_matrix);
            let position_loss = position.value * correlated_shock * position.volatility;
            total_loss += position_loss;
        }
        
        total_loss
    }

    fn apply_correlation(&self, shock: f64, asset_index: usize, correlation_matrix: &DMatrix<f64>) -> f64 {
        if asset_index < correlation_matrix.nrows() {
            shock * correlation_matrix[(asset_index, asset_index)]
        } else {
            shock
        }
    }

    pub async fn stress_test(&self, positions: &[Position]) -> Result<StressTestResults> {
        let mut results = StressTestResults::new();
        
        for scenario in &self.stress_scenarios {
            let stressed_loss = self.apply_stress_scenario(positions, scenario).await?;
            results.add_scenario_result(scenario.name.clone(), stressed_loss);
        }
        
        Ok(results)
    }

    async fn apply_stress_scenario(&self, positions: &[Position], scenario: &StressScenario) -> Result<f64> {
        let mut total_loss = 0.0;
        
        for position in positions {
            let market_impact = position.value * scenario.market_shock_pct;
            let liquidity_impact = position.value * scenario.liquidity_shock_pct * 0.5;
            total_loss += market_impact + liquidity_impact;
        }
        
        Ok(total_loss)
    }

    fn default_limits() -> HashMap<String, PositionLimit> {
        let mut limits = HashMap::new();
        
        limits.insert("BTC".to_string(), PositionLimit {
            max_position_usd: 100000.0,
            max_daily_volume_usd: 500000.0,
            max_leverage: 3.0,
            sector_limit: 0.3,
        });
        
        limits.insert("ETH".to_string(), PositionLimit {
            max_position_usd: 75000.0,
            max_daily_volume_usd: 300000.0,
            max_leverage: 3.0,
            sector_limit: 0.25,
        });
        
        limits
    }

    fn default_stress_scenarios() -> Vec<StressScenario> {
        vec![
            StressScenario {
                name: "Market Crash".to_string(),
                market_shock_pct: -0.2,
                correlation_shock: 0.9,
                liquidity_shock_pct: 0.5,
            },
            StressScenario {
                name: "Flash Crash".to_string(),
                market_shock_pct: -0.1,
                correlation_shock: 0.95,
                liquidity_shock_pct: 0.8,
            },
            StressScenario {
                name: "Correlation Breakdown".to_string(),
                market_shock_pct: -0.05,
                correlation_shock: 0.1,
                liquidity_shock_pct: 0.3,
            },
        ]
    }
}

#[derive(Debug, Clone)]
pub struct Position {
    pub symbol: String,
    pub value: f64,
    pub volatility: f64,
    pub beta: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct StressTestResults {
    scenario_results: HashMap<String, f64>,
    worst_case_loss: f64,
    expected_shortfall: f64,
}

impl StressTestResults {
    pub fn new() -> Self {
        Self {
            scenario_results: HashMap::new(),
            worst_case_loss: 0.0,
            expected_shortfall: 0.0,
        }
    }

    pub fn add_scenario_result(&mut self, scenario: String, loss: f64) {
        self.scenario_results.insert(scenario, loss);
        if loss > self.worst_case_loss {
            self.worst_case_loss = loss;
        }
    }
}
