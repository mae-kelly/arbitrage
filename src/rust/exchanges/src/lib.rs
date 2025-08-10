use anyhow::Result;
use async_trait::async_trait;
use rust_decimal::Decimal;
use tracing::info;
use rand::Rng;

pub struct MockExchange {
    name: String,
}

impl MockExchange {
    pub fn new(name: String) -> Self {
        Self { name }
    }
    
    pub fn generate_price(&self) -> f64 {
        let mut rng = rand::thread_rng();
        50000.0 * (1.0 + (rng.gen::<f64>() - 0.5) * 0.01)
    }
}
