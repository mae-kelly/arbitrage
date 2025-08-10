pub mod statistical;
pub mod triangular;
pub mod funding_rate;

use anyhow::Result;
use ethers::types::{U256, Address};
use std::collections::HashMap;

#[derive(Clone, Debug)]
pub struct StrategyEngine {
    strategies: HashMap<String, Box<dyn Strategy>>,
}

pub trait Strategy: Send + Sync {
    fn evaluate(&self, market_data: &MarketData) -> Result<Vec<Signal>>;
}

#[derive(Debug)]
pub struct MarketData {
    pub prices: HashMap<String, f64>,
    pub volumes: HashMap<String, f64>,
}

#[derive(Debug)]
pub struct Signal {
    pub action: String,
    pub confidence: f64,
}
