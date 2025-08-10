use tokio_tungstenite::connect_async;
use futures_util::{StreamExt, SinkExt};
use serde::Deserialize;
use std::sync::Arc;
use dashmap::DashMap;
use tokio::sync::broadcast;

#[derive(Debug, Clone)]
pub struct PriceUpdate {
    pub exchange: String,
    pub pair: String,
    pub bid: f64,
    pub ask: f64,
    pub timestamp: i64,
    pub layer: Layer,
}

#[derive(Debug, Clone)]
pub enum Layer {
    L1Cex,
    L1Dex,
    L2Arbitrum,
    L2Optimism,
    L2Polygon,
    L2Base,
}

pub struct WebSocketManager {
    pub prices: Arc<DashMap<String, PriceUpdate>>,  // Made public
    tx: broadcast::Sender<PriceUpdate>,
}

impl WebSocketManager {
    pub fn new() -> (Self, broadcast::Receiver<PriceUpdate>) {
        let (tx, rx) = broadcast::channel(10000);
        (
            Self {
                prices: Arc::new(DashMap::new()),
                tx,
            },
            rx
        )
    }

    pub async fn connect_all_feeds(&self) {
        tokio::join!(
            self.connect_binance(),
            self.connect_coinbase(),
            self.connect_kraken(),
        );
    }

    async fn connect_binance(&self) {
        let url = "wss://stream.binance.com:9443/ws/btcusdt@bookTicker";
        let prices = self.prices.clone();
        let tx = self.tx.clone();
        
        tokio::spawn(async move {
            loop {
                if let Ok((ws_stream, _)) = connect_async(url).await {
                    let (_, mut read) = ws_stream.split();
                    while let Some(msg) = read.next().await {
                        if let Ok(msg) = msg {
                            if let Ok(text) = msg.to_text() {
                                if let Ok(data) = serde_json::from_str::<BinanceBookTicker>(text) {
                                    let update = PriceUpdate {
                                        exchange: "Binance".to_string(),
                                        pair: "BTC/USDT".to_string(),
                                        bid: data.bid_price.parse().unwrap_or(0.0),
                                        ask: data.ask_price.parse().unwrap_or(0.0),
                                        timestamp: chrono::Utc::now().timestamp_millis(),
                                        layer: Layer::L1Cex,
                                    };
                                    prices.insert("binance_btcusdt".to_string(), update.clone());
                                    let _ = tx.send(update);
                                }
                            }
                        }
                    }
                }
                tokio::time::sleep(tokio::time::Duration::from_secs(1)).await;
            }
        });
    }

    async fn connect_coinbase(&self) {
        let url = "wss://ws-feed.exchange.coinbase.com";
        let prices = self.prices.clone();
        let tx = self.tx.clone();
        
        tokio::spawn(async move {
            loop {
                if let Ok((mut ws_stream, _)) = connect_async(url).await {
                    let subscribe = r#"{
                        "type": "subscribe",
                        "product_ids": ["BTC-USD"],
                        "channels": ["ticker"]
                    }"#;
                    
                    let _ = ws_stream.send(tokio_tungstenite::tungstenite::Message::Text(subscribe.to_string())).await;
                    
                    let (_, mut read) = ws_stream.split();
                    while let Some(msg) = read.next().await {
                        if let Ok(msg) = msg {
                            if let Ok(text) = msg.to_text() {
                                if let Ok(data) = serde_json::from_str::<CoinbaseTicker>(text) {
                                    if data.r#type == "ticker" {
                                        let update = PriceUpdate {
                                            exchange: "Coinbase".to_string(),
                                            pair: "BTC/USD".to_string(),
                                            bid: data.best_bid.parse().unwrap_or(0.0),
                                            ask: data.best_ask.parse().unwrap_or(0.0),
                                            timestamp: chrono::Utc::now().timestamp_millis(),
                                            layer: Layer::L1Cex,
                                        };
                                        prices.insert("coinbase_btcusd".to_string(), update.clone());
                                        let _ = tx.send(update);
                                    }
                                }
                            }
                        }
                    }
                }
                tokio::time::sleep(tokio::time::Duration::from_secs(1)).await;
            }
        });
    }

    async fn connect_kraken(&self) {
        // Simplified Kraken implementation for now
        let prices = self.prices.clone();
        let tx = self.tx.clone();
        
        tokio::spawn(async move {
            let client = reqwest::Client::new();
            loop {
                if let Ok(resp) = client
                    .get("https://api.kraken.com/0/public/Ticker?pair=XBTUSD")
                    .send()
                    .await
                {
                    if let Ok(json) = resp.json::<serde_json::Value>().await {
                        if let Some(price_str) = json["result"]["XXBTZUSD"]["c"][0].as_str() {
                            if let Ok(price) = price_str.parse::<f64>() {
                                let update = PriceUpdate {
                                    exchange: "Kraken".to_string(),
                                    pair: "BTC/USD".to_string(),
                                    bid: price - 10.0,  // Simulated spread
                                    ask: price + 10.0,
                                    timestamp: chrono::Utc::now().timestamp_millis(),
                                    layer: Layer::L1Cex,
                                };
                                prices.insert("kraken_btcusd".to_string(), update.clone());
                                let _ = tx.send(update);
                            }
                        }
                    }
                }
                tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
            }
        });
    }
}

#[derive(Deserialize)]
struct BinanceBookTicker {
    #[serde(rename = "b")]
    bid_price: String,
    #[serde(rename = "a")]
    ask_price: String,
}

#[derive(Deserialize)]
struct CoinbaseTicker {
    r#type: String,
    best_bid: String,
    best_ask: String,
}
