use anyhow::Result;
use tokio_tungstenite::{connect_async, tungstenite::Message};
use futures::{StreamExt, SinkExt};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;
use dashmap::DashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PriceFeed {
    pub pair: String,
    pub price: f64,
    pub volume: f64,
    pub timestamp: u64,
}

pub struct WebSocketFeed {
    feeds: Arc<DashMap<String, PriceFeed>>,
    connections: Arc<RwLock<Vec<String>>>,
}

impl WebSocketFeed {
    pub async fn new() -> Result<Self> {
        let feeds = Arc::new(DashMap::new());
        let connections = vec![
            "wss://stream.binance.com:9443/ws/ethusdt@trade".to_string(),
            "wss://ws-feed.exchange.coinbase.com".to_string(),
            "wss://api.kraken.com/ws".to_string(),
        ];
        
        Ok(Self {
            feeds,
            connections: Arc::new(RwLock::new(connections)),
        })
    }
    
    pub async fn connect_all(&self) -> Result<()> {
        let connections = self.connections.read().await;
        
        for url in connections.iter() {
            let feeds = self.feeds.clone();
            let url_clone = url.clone();
            
            tokio::spawn(async move {
                if let Err(e) = Self::connect_single(&url_clone, feeds).await {
                    tracing::error!("WebSocket connection failed: {}", e);
                }
            });
        }
        
        Ok(())
    }
    
    async fn connect_single(url: &str, feeds: Arc<DashMap<String, PriceFeed>>) -> Result<()> {
        let (ws_stream, _) = connect_async(url).await?;
        let (mut write, mut read) = ws_stream.split();
        
        if url.contains("coinbase") {
            let subscribe_msg = serde_json::json!({
                "type": "subscribe",
                "product_ids": ["ETH-USD", "BTC-USD"],
                "channels": ["ticker"]
            });
            write.send(Message::Text(subscribe_msg.to_string())).await?;
        } else if url.contains("kraken") {
            let subscribe_msg = serde_json::json!({
                "event": "subscribe",
                "pair": ["ETH/USD", "BTC/USD"],
                "subscription": {"name": "ticker"}
            });
            write.send(Message::Text(subscribe_msg.to_string())).await?;
        }
        
        while let Some(msg) = read.next().await {
            match msg {
                Ok(Message::Text(text)) => {
                    if let Ok(json) = serde_json::from_str::<serde_json::Value>(&text) {
                        Self::process_message(json, &feeds);
                    }
                }
                Err(e) => {
                    tracing::error!("WebSocket error: {}", e);
                    break;
                }
                _ => {}
            }
        }
        
        Ok(())
    }
    
    fn process_message(msg: serde_json::Value, feeds: &Arc<DashMap<String, PriceFeed>>) {
        if let Some(symbol) = msg.get("s").and_then(|s| s.as_str()) {
            if let Some(price) = msg.get("p").and_then(|p| p.as_str().and_then(|s| s.parse::<f64>().ok())) {
                let feed = PriceFeed {
                    pair: symbol.to_string(),
                    price,
                    volume: msg.get("q").and_then(|q| q.as_str().and_then(|s| s.parse().ok())).unwrap_or(0.0),
                    timestamp: chrono::Utc::now().timestamp() as u64,
                };
                feeds.insert(symbol.to_string(), feed);
            }
        }
    }
    
    pub fn get_price(&self, pair: &str) -> Option<PriceFeed> {
        self.feeds.get(pair).map(|entry| entry.value().clone())
    }
}
