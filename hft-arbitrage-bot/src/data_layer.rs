//! Simplified Data Layer for educational demo

use anyhow::Result;
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use tokio::sync::broadcast;
use tracing::info;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketData {
    pub venue: String,
    pub chain_id: Option<u64>,
    pub symbol: String,
    pub price: f64,
    pub volume: f64,
    pub timestamp: u64,
}

pub struct DataLayer {
    market_data: HashMap<String, MarketData>,
    _sender: broadcast::Sender<MarketData>,
}

impl DataLayer {
    pub fn new() -> (Self, broadcast::Receiver<MarketData>) {
        let (tx, rx) = broadcast::channel(1000);
        (Self {
            market_data: HashMap::new(),
            _sender: tx,
        }, rx)
    }

    pub async fn initialize_all_feeds(&mut self) -> Result<()> {
        info!("📊 Initializing data feeds for 6 chains and 10+ exchanges");
        Ok(())
    }

    pub async fn get_latest_market_data(&self) -> Result<Vec<MarketData>> {
        // Simulate market data from multiple chains and exchanges
        Ok(vec![
            MarketData {
                venue: "binance".to_string(),
                chain_id: None,
                symbol: "BTC-USDT".to_string(),
                price: 43000.0 + (rand::random::<f64>() - 0.5) * 100.0,
                volume: 1000000.0,
                timestamp: chrono::Utc::now().timestamp() as u64,
            },
            MarketData {
                venue: "uniswap_v3".to_string(),
                chain_id: Some(1),
                symbol: "BTC-USDT".to_string(),
                price: 43050.0 + (rand::random::<f64>() - 0.5) * 100.0,
                volume: 500000.0,
                timestamp: chrono::Utc::now().timestamp() as u64,
            },
        ])
    }
}
