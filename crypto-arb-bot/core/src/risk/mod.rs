use anyhow::Result;
use std::collections::HashMap;

pub struct RiskManager {
    max_position_size: f64,
    max_daily_loss: f64,
    current_positions: HashMap<String, Position>,
    daily_pnl: f64,
}

#[derive(Clone, Debug)]
pub struct Position {
    pub symbol: String,
    pub size: f64,
    pub entry_price: f64,
    pub current_price: f64,
    pub unrealized_pnl: f64,
}

impl RiskManager {
    pub fn new() -> Self {
        Self {
            max_position_size: 1000000.0,
            max_daily_loss: 50000.0,
            current_positions: HashMap::new(),
            daily_pnl: 0.0,
        }
    }
    
    pub fn can_trade(&self, size: f64) -> bool {
        if size > self.max_position_size {
            return false;
        }
        
        if self.daily_pnl < -self.max_daily_loss {
            return false;
        }
        
        true
    }
    
    pub fn add_position(&mut self, position: Position) {
        self.current_positions.insert(position.symbol.clone(), position);
    }
    
    pub fn update_pnl(&mut self, pnl: f64) {
        self.daily_pnl += pnl;
    }
}
