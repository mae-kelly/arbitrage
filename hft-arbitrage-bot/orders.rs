//! Order management types and structures

use serde::{Serialize, Deserialize};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderRequest {
    pub symbol: String,
    pub side: OrderSide,
    pub order_type: OrderType,
    pub quantity: f64,
    pub price: Option<f64>,
    pub time_in_force: TimeInForce,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderResponse {
    pub order_id: String,
    pub client_order_id: String,
    pub symbol: String,
    pub status: OrderStatus,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderFill {
    pub order_id: String,
    pub symbol: String,
    pub side: OrderSide,
    pub status: OrderStatus,
    pub filled_quantity: f64,
    pub average_price: f64,
    pub commission: f64,
    pub commission_asset: String,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum OrderSide {
    Buy,
    Sell,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum OrderType {
    Market,
    Limit,
    StopLoss,
    StopLossLimit,
    TakeProfit,
    TakeProfitLimit,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum OrderStatus {
    New,
    PartiallyFilled,
    Filled,
    Cancelled,
    Rejected,
    Expired,
    Failed,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TimeInForce {
    GTC, // Good Till Canceled
    IOC, // Immediate Or Cancel
    FOK, // Fill Or Kill
    GTX, // Good Till Crossing
}

impl OrderFill {
    pub fn simulated(strategy: &crate::production::trading::engine::ArbitrageStrategy, price: f64, side: OrderSide) -> Self {
        Self {
            order_id: Uuid::new_v4().to_string(),
            symbol: strategy.symbol.clone(),
            side,
            status: OrderStatus::Filled,
            filled_quantity: strategy.quantity,
            average_price: price,
            commission: strategy.position_size_usd * 0.001, // 0.1% commission
            commission_asset: "USD".to_string(),
            created_at: chrono::Utc::now(),
            updated_at: chrono::Utc::now(),
        }
    }
}
