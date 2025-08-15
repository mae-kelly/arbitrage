//! Authenticated exchange client implementations

pub mod coinbase;
pub mod kraken;
pub mod kucoin;
pub mod binance;

use async_trait::async_trait;
use anyhow::Result;
use serde::{Serialize, Deserialize};

pub use crate::production::trading::orders::*;

#[async_trait]
pub trait AuthenticatedExchange: Send + Sync {
    async fn test_connection(&self) -> Result<()>;
    async fn get_account_info(&self) -> Result<AccountInfo>;
    async fn get_balances(&self) -> Result<Vec<Balance>>;
    async fn place_order(&self, order: OrderRequest) -> Result<OrderResponse>;
    async fn cancel_order(&self, order_id: &str) -> Result<()>;
    async fn cancel_all_orders(&self) -> Result<()>;
    async fn get_order_status(&self, order_id: &str) -> Result<OrderFill>;
    async fn get_open_orders(&self) -> Result<Vec<OrderFill>>;
    async fn get_order_history(&self, symbol: Option<&str>) -> Result<Vec<OrderFill>>;
    async fn get_trading_fees(&self) -> Result<TradingFees>;
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AccountInfo {
    pub account_id: String,
    pub account_type: String,
    pub trading_enabled: bool,
    pub permissions: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Balance {
    pub asset: String,
    pub free: f64,
    pub locked: f64,
    pub total: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradingFees {
    pub maker_fee: f64,
    pub taker_fee: f64,
    pub currency: String,
}

#[derive(Debug, Clone)]
pub struct ExchangeCredentials {
    pub api_key: String,
    pub secret_key: String,
    pub passphrase: Option<String>,
    pub sandbox: bool,
}
