#!/bin/bash
# Advanced exchange connector generator

EXCHANGE_NAME=$1
WS_URL=${2:-"wss://ws.${EXCHANGE_NAME}.com"}
API_URL=${3:-"https://api.${EXCHANGE_NAME}.com"}

if [ -z "$EXCHANGE_NAME" ]; then
    echo "Usage: ./add_exchange.sh <exchange_name> [ws_url] [api_url]"
    exit 1
fi

echo "🔗 Creating exchange connector: $EXCHANGE_NAME"

mkdir -p src/exchanges

cat > "src/exchanges/${EXCHANGE_NAME}.rs" << EXCHANGE_EOF
//! ${EXCHANGE_NAME^} Exchange Connector
//! Ultra-high performance WebSocket and REST API integration

use anyhow::Result;
use async_trait::async_trait;
use dashmap::DashMap;
use futures_util::{SinkExt, StreamExt};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;
use tokio_tungstenite::{connect_async, tungstenite::Message};
use tracing::{info, warn, error, debug, instrument};
use url::Url;

const WS_URL: &str = "$WS_URL";
const API_URL: &str = "$API_URL";

#[derive(Debug, Clone)]
pub struct ${EXCHANGE_NAME^}Connector {
    ws_connection: Arc<RwLock<Option<WebSocketConnection>>>,
    subscriptions: Arc<DashMap<String, SubscriptionType>>,
    rate_limiter: Arc<RateLimiter>,
}

#[derive(Debug)]
struct WebSocketConnection {
    // WebSocket connection details
}

#[derive(Debug, Clone)]
enum SubscriptionType {
    Ticker,
    OrderBook,
    Trades,
}

struct RateLimiter {
    // Rate limiting implementation
}

#[derive(Debug, Deserialize)]
struct ${EXCHANGE_NAME^}Ticker {
    symbol: String,
    price: String,
    bid: String,
    ask: String,
    volume: String,
}

impl ${EXCHANGE_NAME^}Connector {
    pub fn new() -> Self {
        Self {
            ws_connection: Arc::new(RwLock::new(None)),
            subscriptions: Arc::new(DashMap::new()),
            rate_limiter: Arc::new(RateLimiter {}),
        }
    }
    
    #[instrument(skip(self))]
    pub async fn connect(&self) -> Result<()> {
        info!("🔗 Connecting to {} at {}", stringify!($EXCHANGE_NAME), WS_URL);
        
        let url = Url::parse(WS_URL)?;
        let (ws_stream, _) = connect_async(url).await?;
        
        // Store connection
        *self.ws_connection.write().await = Some(WebSocketConnection {});
        
        info!("✅ Connected to {}", stringify!($EXCHANGE_NAME));
        Ok(())
    }
    
    #[instrument(skip(self))]
    pub async fn subscribe_ticker(&self, symbol: &str) -> Result<()> {
        info!("📊 Subscribing to {} ticker: {}", stringify!($EXCHANGE_NAME), symbol);
        
        // Add subscription logic here
        self.subscriptions.insert(symbol.to_string(), SubscriptionType::Ticker);
        
        Ok(())
    }
    
    pub async fn get_ticker(&self, symbol: &str) -> Result<MarketTicker> {
        // Implement ticker fetching
        Ok(MarketTicker {
            symbol: symbol.to_string(),
            exchange: stringify!($EXCHANGE_NAME).to_string(),
            price: 0.0,
            bid: 0.0,
            ask: 0.0,
            volume: 0.0,
            timestamp: chrono::Utc::now(),
        })
    }
    
    pub fn get_exchange_info(&self) -> ExchangeInfo {
        ExchangeInfo {
            name: stringify!($EXCHANGE_NAME).to_string(),
            ws_url: WS_URL.to_string(),
            api_url: API_URL.to_string(),
            is_connected: false, // TODO: Check actual connection status
            subscriptions: self.subscriptions.len(),
        }
    }
}

#[derive(Debug, Serialize)]
pub struct ExchangeInfo {
    pub name: String,
    pub ws_url: String,
    pub api_url: String,
    pub is_connected: bool,
    pub subscriptions: usize,
}

#[derive(Debug, Clone)]
pub struct MarketTicker {
    pub symbol: String,
    pub exchange: String,
    pub price: f64,
    pub bid: f64,
    pub ask: f64,
    pub volume: f64,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_${EXCHANGE_NAME}_connection() {
        let connector = ${EXCHANGE_NAME^}Connector::new();
        // Add connection tests
    }
}
EXCHANGE_EOF

# Add to exchanges module
if [ ! -f "src/exchanges/mod.rs" ]; then
    echo "//! Exchange connectors" > "src/exchanges/mod.rs"
fi

echo "pub mod $EXCHANGE_NAME;" >> "src/exchanges/mod.rs"
echo "pub use $EXCHANGE_NAME::*;" >> "src/exchanges/mod.rs"

echo "✅ Created src/exchanges/${EXCHANGE_NAME}.rs"
echo "🔗 Added to exchanges module"
