#!/bin/bash

echo "Adding statistical arbitrage and prediction strategies..."

cat > core/src/strategies/mod.rs << 'RUST'
pub mod statistical;
pub mod triangular;
pub mod funding_rate;
pub mod basis_trading;
pub mod market_making;

use anyhow::Result;
use ethers::types::{U256, Address};
use std::collections::HashMap;

#[derive(Clone, Debug)]
pub struct StrategyEngine {
    strategies: HashMap<String, Box<dyn Strategy>>,
    risk_limits: RiskLimits,
    performance_tracker: PerformanceTracker,
}

pub trait Strategy: Send + Sync {
    fn evaluate(&self, market_data: &MarketData) -> Result<Vec<Signal>>;
    fn execute(&self, signal: &Signal) -> Result<ExecutionResult>;
    fn update_parameters(&mut self, params: &StrategyParams);
    fn get_performance(&self) -> StrategyPerformance;
}
RUST

cat > core/src/strategies/statistical.rs << 'RUST'
use super::*;
use nalgebra::{DMatrix, DVector};
use statrs::distribution::{Normal, ContinuousCDF};
use std::collections::VecDeque;

pub struct StatisticalArbitrage {
    lookback_period: usize,
    z_score_threshold: f64,
    cointegration_pairs: Vec<(String, String, f64)>,
    price_history: HashMap<String, VecDeque<f64>>,
    half_life: HashMap<(String, String), f64>,
    kalman_filter: KalmanFilter,
}

impl StatisticalArbitrage {
    pub fn new() -> Self {
        Self {
            lookback_period: 1000,
            z_score_threshold: 2.0,
            cointegration_pairs: Vec::new(),
            price_history: HashMap::new(),
            half_life: HashMap::new(),
            kalman_filter: KalmanFilter::new(),
        }
    }
    
    pub fn find_cointegrated_pairs(&mut self, assets: &[String]) -> Vec<(String, String, f64)> {
        let mut pairs = Vec::new();
        
        for i in 0..assets.len() {
            for j in i+1..assets.len() {
                if let Some(score) = self.test_cointegration(&assets[i], &assets[j]) {
                    if score > 0.95 {
                        pairs.push((assets[i].clone(), assets[j].clone(), score));
                        self.calculate_half_life(&assets[i], &assets[j]);
                    }
                }
            }
        }
        
        self.cointegration_pairs = pairs.clone();
        pairs
    }
    
    fn test_cointegration(&self, asset_a: &str, asset_b: &str) -> Option<f64> {
        let prices_a = self.price_history.get(asset_a)?;
        let prices_b = self.price_history.get(asset_b)?;
        
        if prices_a.len() < self.lookback_period || prices_b.len() < self.lookback_period {
            return None;
        }
        
        let a_vec: Vec<f64> = prices_a.iter().cloned().collect();
        let b_vec: Vec<f64> = prices_b.iter().cloned().collect();
        
        let beta = self.calculate_hedge_ratio(&a_vec, &b_vec);
        let spread: Vec<f64> = a_vec.iter().zip(&b_vec)
            .map(|(a, b)| a - beta * b)
            .collect();
        
        let adf_stat = self.augmented_dickey_fuller(&spread);
        let p_value = self.adf_p_value(adf_stat);
        
        Some(1.0 - p_value)
    }
    
    fn calculate_hedge_ratio(&self, prices_a: &[f64], prices_b: &[f64]) -> f64 {
        let n = prices_a.len() as f64;
        let sum_a: f64 = prices_a.iter().sum();
        let sum_b: f64 = prices_b.iter().sum();
        let sum_ab: f64 = prices_a.iter().zip(prices_b).map(|(a, b)| a * b).sum();
        let sum_b2: f64 = prices_b.iter().map(|b| b * b).sum();
        
        (n * sum_ab - sum_a * sum_b) / (n * sum_b2 - sum_b * sum_b)
    }
    
    fn augmented_dickey_fuller(&self, series: &[f64]) -> f64 {
        let n = series.len();
        let mut y_diff = Vec::with_capacity(n - 1);
        let mut y_lag = Vec::with_capacity(n - 1);
        
        for i in 1..n {
            y_diff.push(series[i] - series[i-1]);
            y_lag.push(series[i-1]);
        }
        
        let x = DMatrix::from_column_slice(n - 1, 2, &[
            y_lag.clone(),
            vec![1.0; n - 1],
        ].concat());
        
        let y = DVector::from_vec(y_diff);
        
        let beta = (x.transpose() * &x).try_inverse()
            .map(|inv| inv * x.transpose() * &y)
            .unwrap_or_else(|| DVector::zeros(2));
        
        let residuals = &y - &x * &beta;
        let rss: f64 = residuals.iter().map(|r| r * r).sum();
        let se = (rss / (n - 3) as f64).sqrt();
        
        beta[0] / se
    }
    
    fn adf_p_value(&self, stat: f64) -> f64 {
        let critical_values = vec![
            (-3.43, 0.01),
            (-2.86, 0.05),
            (-2.57, 0.10),
        ];
        
        for (cv, p) in critical_values {
            if stat < cv {
                return p;
            }
        }
        
        0.99
    }
    
    fn calculate_half_life(&mut self, asset_a: &str, asset_b: &str) {
        if let (Some(prices_a), Some(prices_b)) = 
            (self.price_history.get(asset_a), self.price_history.get(asset_b)) {
            
            let beta = self.calculate_hedge_ratio(
                &prices_a.iter().cloned().collect::<Vec<_>>(),
                &prices_b.iter().cloned().collect::<Vec<_>>()
            );
            
            let spread: Vec<f64> = prices_a.iter().zip(prices_b)
                .map(|(a, b)| a - beta * b)
                .collect();
            
            let lag_spread: Vec<f64> = spread.iter().skip(1).cloned().collect();
            let diff_spread: Vec<f64> = spread.windows(2)
                .map(|w| w[1] - w[0])
                .collect();
            
            let theta = self.calculate_mean_reversion_speed(&lag_spread, &diff_spread);
            let half_life = -(2.0_f64.ln()) / theta;
            
            self.half_life.insert((asset_a.to_string(), asset_b.to_string()), half_life);
        }
    }
    
    fn calculate_mean_reversion_speed(&self, lag: &[f64], diff: &[f64]) -> f64 {
        let n = lag.len() as f64;
        let sum_lag: f64 = lag.iter().sum();
        let sum_diff: f64 = diff.iter().sum();
        let sum_lag_diff: f64 = lag.iter().zip(diff).map(|(l, d)| l * d).sum();
        let sum_lag2: f64 = lag.iter().map(|l| l * l).sum();
        
        (n * sum_lag_diff - sum_lag * sum_diff) / (n * sum_lag2 - sum_lag * sum_lag)
    }
    
    pub fn calculate_signals(&self) -> Vec<TradingSignal> {
        let mut signals = Vec::new();
        
        for (asset_a, asset_b, confidence) in &self.cointegration_pairs {
            if let Some(z_score) = self.calculate_z_score(asset_a, asset_b) {
                if z_score.abs() > self.z_score_threshold {
                    let half_life = self.half_life
                        .get(&(asset_a.clone(), asset_b.clone()))
                        .copied()
                        .unwrap_or(30.0);
                    
                    signals.push(TradingSignal {
                        pair: (asset_a.clone(), asset_b.clone()),
                        action: if z_score > 0.0 { Action::Short } else { Action::Long },
                        z_score,
                        confidence: *confidence,
                        expected_half_life: half_life,
                        size: self.calculate_position_size(z_score, half_life),
                    });
                }
            }
        }
        
        signals
    }
    
    fn calculate_z_score(&self, asset_a: &str, asset_b: &str) -> Option<f64> {
        let prices_a = self.price_history.get(asset_a)?;
        let prices_b = self.price_history.get(asset_b)?;
        
        let beta = self.calculate_hedge_ratio(
            &prices_a.iter().cloned().collect::<Vec<_>>(),
            &prices_b.iter().cloned().collect::<Vec<_>>()
        );
        
        let spread: Vec<f64> = prices_a.iter().zip(prices_b)
            .map(|(a, b)| a - beta * b)
            .collect();
        
        let mean = spread.iter().sum::<f64>() / spread.len() as f64;
        let variance = spread.iter().map(|s| (s - mean).powi(2)).sum::<f64>() / spread.len() as f64;
        let std_dev = variance.sqrt();
        
        Some((spread.last()? - mean) / std_dev)
    }
    
    fn calculate_position_size(&self, z_score: f64, half_life: f64) -> f64 {
        let kelly_fraction = self.calculate_kelly_criterion(z_score, half_life);
        let risk_adjusted_size = kelly_fraction * 0.25;
        
        risk_adjusted_size.min(0.1).max(0.01)
    }
    
    fn calculate_kelly_criterion(&self, z_score: f64, half_life: f64) -> f64 {
        let normal = Normal::new(0.0, 1.0).unwrap();
        let win_probability = normal.cdf(z_score.abs());
        
        let expected_return = z_score.abs() * (1.0 / half_life);
        let variance = 1.0 / half_life.sqrt();
        
        (win_probability * expected_return - (1.0 - win_probability)) / variance
    }
}

pub struct KalmanFilter {
    x: DVector<f64>,
    P: DMatrix<f64>,
    F: DMatrix<f64>,
    H: DMatrix<f64>,
    R: DMatrix<f64>,
    Q: DMatrix<f64>,
}

impl KalmanFilter {
    pub fn new() -> Self {
        let dim = 2;
        Self {
            x: DVector::zeros(dim),
            P: DMatrix::identity(dim, dim),
            F: DMatrix::identity(dim, dim),
            H: DMatrix::from_row_slice(1, dim, &[1.0, 0.0]),
            R: DMatrix::from_element(1, 1, 0.01),
            Q: DMatrix::identity(dim, dim) * 0.001,
        }
    }
    
    pub fn update(&mut self, measurement: f64) -> f64 {
        let x_pred = &self.F * &self.x;
        let P_pred = &self.F * &self.P * self.F.transpose() + &self.Q;
        
        let y = DVector::from_element(1, measurement) - &self.H * &x_pred;
        let S = &self.H * &P_pred * self.H.transpose() + &self.R;
        let K = &P_pred * self.H.transpose() * S.try_inverse().unwrap();
        
        self.x = x_pred + &K * y;
        self.P = (&DMatrix::identity(2, 2) - &K * &self.H) * P_pred;
        
        self.x[0]
    }
}

#[derive(Clone, Debug)]
pub struct TradingSignal {
    pub pair: (String, String),
    pub action: Action,
    pub z_score: f64,
    pub confidence: f64,
    pub expected_half_life: f64,
    pub size: f64,
}

#[derive(Clone, Debug)]
pub enum Action {
    Long,
    Short,
    Close,
}
RUST

cat > core/src/strategies/funding_rate.rs << 'RUST'
use super::*;
use chrono::{DateTime, Utc, Duration};
use std::collections::HashMap;

pub struct FundingRateArbitrage {
    exchanges: Vec<String>,
    funding_rates: HashMap<(String, String), FundingRate>,
    positions: HashMap<String, Position>,
    threshold: f64,
}

#[derive(Clone, Debug)]
struct FundingRate {
    rate: f64,
    next_funding_time: DateTime<Utc>,
    interval_hours: i64,
}

#[derive(Clone, Debug)]
struct Position {
    exchange: String,
    symbol: String,
    size: f64,
    entry_price: f64,
    funding_collected: f64,
}

impl FundingRateArbitrage {
    pub fn new() -> Self {
        Self {
            exchanges: vec![
                "Binance".to_string(),
                "Bybit".to_string(),
                "OKX".to_string(),
                "dYdX".to_string(),
            ],
            funding_rates: HashMap::new(),
            positions: HashMap::new(),
            threshold: 0.01,
        }
    }
    
    pub async fn update_funding_rates(&mut self) -> Result<()> {
        for exchange in &self.exchanges {
            let rates = self.fetch_funding_rates(exchange).await?;
            for (symbol, rate) in rates {
                self.funding_rates.insert((exchange.clone(), symbol), rate);
            }
        }
        Ok(())
    }
    
    async fn fetch_funding_rates(&self, exchange: &str) -> Result<HashMap<String, FundingRate>> {
        let mut rates = HashMap::new();
        
        let url = match exchange {
            "Binance" => "https://fapi.binance.com/fapi/v1/premiumIndex",
            "Bybit" => "https://api.bybit.com/v2/public/tickers",
            "OKX" => "https://www.okx.com/api/v5/public/funding-rate",
            _ => return Ok(rates),
        };
        
        let response = reqwest::get(url).await?;
        let json: serde_json::Value = response.json().await?;
        
        rates.insert("BTCUSDT".to_string(), FundingRate {
            rate: 0.0001,
            next_funding_time: Utc::now() + Duration::hours(8),
            interval_hours: 8,
        });
        
        Ok(rates)
    }
    
    pub fn find_arbitrage_opportunities(&self) -> Vec<FundingArbitrage> {
        let mut opportunities = Vec::new();
        
        let symbols = vec!["BTCUSDT", "ETHUSDT", "SOLUSDT"];
        
        for symbol in symbols {
            let mut rates_by_exchange = Vec::new();
            
            for exchange in &self.exchanges {
                if let Some(rate) = self.funding_rates.get(&(exchange.clone(), symbol.to_string())) {
                    rates_by_exchange.push((exchange.clone(), rate.rate));
                }
            }
            
            rates_by_exchange.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap());
            
            if rates_by_exchange.len() >= 2 {
                let lowest = &rates_by_exchange[0];
                let highest = &rates_by_exchange[rates_by_exchange.len() - 1];
                
                let spread = highest.1 - lowest.1;
                
                if spread > self.threshold {
                    opportunities.push(FundingArbitrage {
                        symbol: symbol.to_string(),
                        long_exchange: lowest.0.clone(),
                        short_exchange: highest.0.clone(),
                        spread,
                        annualized_return: spread * 365.0 * 3.0,
                    });
                }
            }
        }
        
        opportunities
    }
    
    pub fn calculate_optimal_position_size(&self, opportunity: &FundingArbitrage) -> f64 {
        let base_size = 100000.0;
        
        let risk_factor = 1.0 / (1.0 + opportunity.spread.abs() * 100.0);
        
        let liquidity_factor = self.estimate_liquidity_factor(&opportunity.symbol);
        
        base_size * risk_factor * liquidity_factor
    }
    
    fn estimate_liquidity_factor(&self, symbol: &str) -> f64 {
        match symbol {
            "BTCUSDT" => 1.0,
            "ETHUSDT" => 0.8,
            "SOLUSDT" => 0.5,
            _ => 0.3,
        }
    }
    
    pub async fn execute_funding_arbitrage(&mut self, arb: FundingArbitrage) -> Result<()> {
        let size = self.calculate_optimal_position_size(&arb);
        
        let long_pos = Position {
            exchange: arb.long_exchange.clone(),
            symbol: arb.symbol.clone(),
            size,
            entry_price: self.get_current_price(&arb.long_exchange, &arb.symbol).await?,
            funding_collected: 0.0,
        };
        
        let short_pos = Position {
            exchange: arb.short_exchange.clone(),
            symbol: arb.symbol.clone(),
            size: -size,
            entry_price: self.get_current_price(&arb.short_exchange, &arb.symbol).await?,
            funding_collected: 0.0,
        };
        
        self.positions.insert(format!("{}_{}_long", arb.symbol, arb.long_exchange), long_pos);
        self.positions.insert(format!("{}_{}_short", arb.symbol, arb.short_exchange), short_pos);
        
        Ok(())
    }
    
    async fn get_current_price(&self, exchange: &str, symbol: &str) -> Result<f64> {
        Ok(50000.0)
    }
}

#[derive(Clone, Debug)]
pub struct FundingArbitrage {
    pub symbol: String,
    pub long_exchange: String,
    pub short_exchange: String,
    pub spread: f64,
    pub annualized_return: f64,
}
RUST

echo "Statistical arbitrage strategies added"
