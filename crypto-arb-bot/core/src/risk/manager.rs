use anyhow::Result;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

pub struct RiskManager {
    max_position_usd: f64,
    max_daily_loss: f64,
    current_exposure: Arc<RwLock<HashMap<String, f64>>>,
    daily_pnl: Arc<RwLock<f64>>,
    trade_count: Arc<RwLock<u64>>,
}

impl RiskManager {
    pub fn new(max_position: f64, max_daily_loss: f64) -> Self {
        Self {
            max_position_usd: max_position,
            max_daily_loss,
            current_exposure: Arc::new(RwLock::new(HashMap::new())),
            daily_pnl: Arc::new(RwLock::new(0.0)),
            trade_count: Arc::new(RwLock::new(0)),
        }
    }

    pub async fn can_execute_trade(&self, symbol: &str, amount_usd: f64) -> bool {
        let exposure = self.current_exposure.read().await;
        let current = exposure.get(symbol).unwrap_or(&0.0);
        let daily_loss = *self.daily_pnl.read().await;
        
        current + amount_usd <= self.max_position_usd && 
        daily_loss > -self.max_daily_loss
    }

    pub async fn record_trade(&self, symbol: &str, amount_usd: f64, pnl: f64) {
        let mut exposure = self.current_exposure.write().await;
        *exposure.entry(symbol.to_string()).or_insert(0.0) += amount_usd;
        
        let mut daily_pnl = self.daily_pnl.write().await;
        *daily_pnl += pnl;
        
        let mut count = self.trade_count.write().await;
        *count += 1;
    }

    pub async fn emergency_stop(&self) -> bool {
        let daily_loss = *self.daily_pnl.read().await;
        daily_loss < -self.max_daily_loss
    }
}
