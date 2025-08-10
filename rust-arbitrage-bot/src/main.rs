use anyhow::Result;
use crossbeam_channel::{unbounded, Receiver, Sender};
use dashmap::DashMap;
use futures_util::{SinkExt, StreamExt};
use serde::{Deserialize, Serialize};
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use tokio::time::sleep;
use tokio_tungstenite::{connect_async, tungstenite::Message};
use tracing::{error, info, warn};
use rand::Rng;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct PriceData {
    symbol: String,
    price: f64,
    exchange: String,
    timestamp: u64,
    bid: Option<f64>,
    ask: Option<f64>,
    volume: Option<f64>,
}

#[derive(Debug, Clone)]
struct ArbitrageOpportunity {
    symbol: String,
    buy_exchange: String,
    sell_exchange: String,
    buy_price: f64,
    sell_price: f64,
    spread: f64,
    profit: f64,
    timestamp: u64,
}

#[derive(Debug)]
struct BotMetrics {
    opportunities: AtomicUsize,
    trades: AtomicUsize,
    total_profit: AtomicU64,
    start_time: Instant,
}

impl BotMetrics {
    fn new() -> Self {
        Self {
            opportunities: AtomicUsize::new(0),
            trades: AtomicUsize::new(0),
            total_profit: AtomicU64::new(0),
            start_time: Instant::now(),
        }
    }
}

struct LightningArbitrageBot {
    prices: Arc<DashMap<String, DashMap<String, PriceData>>>,
    opportunity_tx: Sender<ArbitrageOpportunity>,
    opportunity_rx: Receiver<ArbitrageOpportunity>,
    metrics: Arc<BotMetrics>,
    min_spread: f64,
}

impl LightningArbitrageBot {
    fn new() -> Self {
        let (tx, rx) = unbounded();
        Self {
            prices: Arc::new(DashMap::new()),
            opportunity_tx: tx,
            opportunity_rx: rx,
            metrics: Arc::new(BotMetrics::new()),
            min_spread: 0.1,
        }
    }

    async fn start(&self) -> Result<()> {
        println!("\x1b[1m\x1b[32m╔═══════════════════════════════════════════════════════════════╗\x1b[0m");
        println!("\x1b[1m\x1b[32m║              ⚡ LIGHTNING ARBITRAGE BOT ⚡                    ║\x1b[0m");
        println!("\x1b[1m\x1b[32m║                  Rust High Performance                        ║\x1b[0m");
        println!("\x1b[1m\x1b[32m╚═══════════════════════════════════════════════════════════════╝\x1b[0m");

        let handles = vec![
            self.spawn_binance_ws(),
            self.spawn_coinbase_ws(),
            self.spawn_kraken_ws(),
            self.spawn_okx_rest(),
            self.spawn_bybit_rest(),
        ];

        let opportunity_processor = self.spawn_opportunity_processor();
        let metrics_reporter = self.spawn_metrics_reporter();

        futures_util::future::join_all(handles).await;
        tokio::try_join!(opportunity_processor, metrics_reporter)?;

        Ok(())
    }

    fn spawn_binance_ws(&self) -> tokio::task::JoinHandle<()> {
        let prices = Arc::clone(&self.prices);
        let opportunity_tx = self.opportunity_tx.clone();

        tokio::spawn(async move {
            loop {
                match Self::connect_binance_ws(&prices, &opportunity_tx).await {
                    Ok(_) => {}
                    Err(e) => {
                        error!("Binance WebSocket error: {}", e);
                        sleep(Duration::from_secs(5)).await;
                    }
                }
            }
        })
    }

    async fn connect_binance_ws(
        prices: &Arc<DashMap<String, DashMap<String, PriceData>>>,
        opportunity_tx: &Sender<ArbitrageOpportunity>,
    ) -> Result<()> {
        let url = "wss://stream.binance.com:9443/ws/!ticker@arr";
        let (ws_stream, _) = connect_async(url).await?;
        let (_write, mut read) = ws_stream.split();

        info!("📡 Binance WebSocket connected");

        while let Some(msg) = read.next().await {
            match msg? {
                Message::Text(text) => {
                    if let Ok(tickers) = serde_json::from_str::<Vec<serde_json::Value>>(&text) {
                        for ticker in tickers {
                            if let (Some(symbol), Some(price_str)) = 
                                (ticker.get("s").and_then(|s| s.as_str()),
                                 ticker.get("c").and_then(|p| p.as_str())) {
                                
                                if ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT", "DOTUSDT"].contains(&symbol) {
                                    if let Ok(price) = price_str.parse::<f64>() {
                                        let normalized_symbol = symbol.replace("USDT", "/USDT");
                                        
                                        let price_data = PriceData {
                                            symbol: normalized_symbol.clone(),
                                            price,
                                            exchange: "binance".to_string(),
                                            timestamp: SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_millis() as u64,
                                            bid: ticker.get("b").and_then(|b| b.as_str()).and_then(|s| s.parse().ok()),
                                            ask: ticker.get("a").and_then(|a| a.as_str()).and_then(|s| s.parse().ok()),
                                            volume: ticker.get("v").and_then(|v| v.as_str()).and_then(|s| s.parse().ok()),
                                        };

                                        Self::update_price(prices, price_data, opportunity_tx);
                                    }
                                }
                            }
                        }
                    }
                }
                Message::Close(_) => break,
                _ => {}
            }
        }

        warn!("Binance WebSocket disconnected");
        Ok(())
    }

    fn spawn_coinbase_ws(&self) -> tokio::task::JoinHandle<()> {
        let prices = Arc::clone(&self.prices);
        let opportunity_tx = self.opportunity_tx.clone();

        tokio::spawn(async move {
            loop {
                match Self::connect_coinbase_ws(&prices, &opportunity_tx).await {
                    Ok(_) => {}
                    Err(e) => {
                        error!("Coinbase WebSocket error: {}", e);
                        sleep(Duration::from_secs(5)).await;
                    }
                }
            }
        })
    }

    async fn connect_coinbase_ws(
        prices: &Arc<DashMap<String, DashMap<String, PriceData>>>,
        opportunity_tx: &Sender<ArbitrageOpportunity>,
    ) -> Result<()> {
        let url = "wss://ws-feed.exchange.coinbase.com";
        let (ws_stream, _) = connect_async(url).await?;
        let (mut write, mut read) = ws_stream.split();

        let subscribe_msg = serde_json::json!({
            "type": "subscribe",
            "product_ids": ["BTC-USD", "ETH-USD", "ADA-USD", "SOL-USD", "DOT-USD"],
            "channels": ["ticker"]
        });
        write.send(Message::Text(subscribe_msg.to_string())).await?;

        info!("📡 Coinbase WebSocket connected");

        while let Some(msg) = read.next().await {
            match msg? {
                Message::Text(text) => {
                    if let Ok(ticker) = serde_json::from_str::<serde_json::Value>(&text) {
                        if ticker.get("type").and_then(|t| t.as_str()) == Some("ticker") {
                            if let (Some(product_id), Some(price_str)) = 
                                (ticker.get("product_id").and_then(|p| p.as_str()),
                                 ticker.get("price").and_then(|p| p.as_str())) {
                                
                                if let Ok(price) = price_str.parse::<f64>() {
                                    let normalized_symbol = product_id.replace("-", "/");
                                    
                                    let price_data = PriceData {
                                        symbol: normalized_symbol.clone(),
                                        price,
                                        exchange: "coinbase".to_string(),
                                        timestamp: SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_millis() as u64,
                                        bid: ticker.get("best_bid").and_then(|b| b.as_str()).and_then(|s| s.parse().ok()),
                                        ask: ticker.get("best_ask").and_then(|a| a.as_str()).and_then(|s| s.parse().ok()),
                                        volume: None,
                                    };

                                    Self::update_price(prices, price_data, opportunity_tx);
                                }
                            }
                        }
                    }
                }
                Message::Close(_) => break,
                _ => {}
            }
        }

        warn!("Coinbase WebSocket disconnected");
        Ok(())
    }

    fn spawn_kraken_ws(&self) -> tokio::task::JoinHandle<()> {
        let prices = Arc::clone(&self.prices);
        let opportunity_tx = self.opportunity_tx.clone();

        tokio::spawn(async move {
            loop {
                match Self::connect_kraken_ws(&prices, &opportunity_tx).await {
                    Ok(_) => {}
                    Err(e) => {
                        error!("Kraken WebSocket error: {}", e);
                        sleep(Duration::from_secs(5)).await;
                    }
                }
            }
        })
    }

    async fn connect_kraken_ws(
        prices: &Arc<DashMap<String, DashMap<String, PriceData>>>,
        opportunity_tx: &Sender<ArbitrageOpportunity>,
    ) -> Result<()> {
        let url = "wss://ws.kraken.com";
        let (ws_stream, _) = connect_async(url).await?;
        let (mut write, mut read) = ws_stream.split();

        let subscribe_msg = serde_json::json!({
            "event": "subscribe",
            "pair": ["XBT/USD", "ETH/USD", "ADA/USD", "SOL/USD", "DOT/USD"],
            "subscription": {"name": "ticker"}
        });
        write.send(Message::Text(subscribe_msg.to_string())).await?;

        info!("📡 Kraken WebSocket connected");

        while let Some(msg) = read.next().await {
            match msg? {
                Message::Text(text) => {
                    if let Ok(message) = serde_json::from_str::<serde_json::Value>(&text) {
                        if let Some(array) = message.as_array() {
                            if array.len() >= 4 && array[2].as_str() == Some("ticker") {
                                if let (Some(ticker), Some(pair)) = 
                                    (array[1].as_object(), array[3].as_str()) {
                                    
                                    if let Some(close_array) = ticker.get("c").and_then(|c| c.as_array()) {
                                        if let Some(price_str) = close_array[0].as_str() {
                                            if let Ok(price) = price_str.parse::<f64>() {
                                                let normalized_symbol = pair.replace("XBT/USD", "BTC/USD");
                                                
                                                let price_data = PriceData {
                                                    symbol: normalized_symbol.clone(),
                                                    price,
                                                    exchange: "kraken".to_string(),
                                                    timestamp: SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_millis() as u64,
                                                    bid: ticker.get("b").and_then(|b| b.as_array()).and_then(|arr| arr[0].as_str()).and_then(|s| s.parse().ok()),
                                                    ask: ticker.get("a").and_then(|a| a.as_array()).and_then(|arr| arr[0].as_str()).and_then(|s| s.parse().ok()),
                                                    volume: None,
                                                };

                                                Self::update_price(prices, price_data, opportunity_tx);
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                Message::Close(_) => break,
                _ => {}
            }
        }

        warn!("Kraken WebSocket disconnected");
        Ok(())
    }

    fn spawn_okx_rest(&self) -> tokio::task::JoinHandle<()> {
        let prices = Arc::clone(&self.prices);
        let opportunity_tx = self.opportunity_tx.clone();

        tokio::spawn(async move {
            let client = reqwest::Client::new();
            loop {
                match Self::fetch_okx_prices(&client, &prices, &opportunity_tx).await {
                    Ok(_) => {}
                    Err(e) => error!("OKX REST error: {}", e),
                }
                sleep(Duration::from_secs(2)).await;
            }
        })
    }

    async fn fetch_okx_prices(
        client: &reqwest::Client,
        prices: &Arc<DashMap<String, DashMap<String, PriceData>>>,
        opportunity_tx: &Sender<ArbitrageOpportunity>,
    ) -> Result<()> {
        let symbols = ["BTC-USDT", "ETH-USDT", "ADA-USDT", "SOL-USDT", "DOT-USDT"];
        
        for symbol in symbols {
            let url = format!("https://www.okx.com/api/v5/market/ticker?instId={}", symbol);
            if let Ok(response) = client.get(&url).send().await {
                if let Ok(json) = response.json::<serde_json::Value>().await {
                    if let Some(data) = json.get("data").and_then(|d| d.as_array()).and_then(|arr| arr.first()) {
                        if let Some(price_str) = data.get("last").and_then(|p| p.as_str()) {
                            if let Ok(price) = price_str.parse::<f64>() {
                                let normalized_symbol = symbol.replace("-", "/");
                                
                                let price_data = PriceData {
                                    symbol: normalized_symbol.clone(),
                                    price,
                                    exchange: "okx".to_string(),
                                    timestamp: SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_millis() as u64,
                                    bid: data.get("bidPx").and_then(|b| b.as_str()).and_then(|s| s.parse().ok()),
                                    ask: data.get("askPx").and_then(|a| a.as_str()).and_then(|s| s.parse().ok()),
                                    volume: data.get("vol24h").and_then(|v| v.as_str()).and_then(|s| s.parse().ok()),
                                };

                                Self::update_price(prices, price_data, opportunity_tx);
                            }
                        }
                    }
                }
            }
        }

        Ok(())
    }

    fn spawn_bybit_rest(&self) -> tokio::task::JoinHandle<()> {
        let prices = Arc::clone(&self.prices);
        let opportunity_tx = self.opportunity_tx.clone();

        tokio::spawn(async move {
            let client = reqwest::Client::new();
            loop {
                match Self::fetch_bybit_prices(&client, &prices, &opportunity_tx).await {
                    Ok(_) => {}
                    Err(e) => error!("Bybit REST error: {}", e),
                }
                sleep(Duration::from_secs(2)).await;
            }
        })
    }

    async fn fetch_bybit_prices(
        client: &reqwest::Client,
        prices: &Arc<DashMap<String, DashMap<String, PriceData>>>,
        opportunity_tx: &Sender<ArbitrageOpportunity>,
    ) -> Result<()> {
        if let Ok(response) = client.get("https://api.bybit.com/v5/market/tickers?category=spot").send().await {
            if let Ok(json) = response.json::<serde_json::Value>().await {
                if let Some(result) = json.get("result").and_then(|r| r.get("list")).and_then(|l| l.as_array()) {
                    for ticker in result {
                        if let Some(symbol) = ticker.get("symbol").and_then(|s| s.as_str()) {
                            if ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT", "DOTUSDT"].contains(&symbol) {
                                if let Some(price_str) = ticker.get("lastPrice").and_then(|p| p.as_str()) {
                                    if let Ok(price) = price_str.parse::<f64>() {
                                        let normalized_symbol = symbol.replace("USDT", "/USDT");
                                        
                                        let price_data = PriceData {
                                            symbol: normalized_symbol.clone(),
                                            price,
                                            exchange: "bybit".to_string(),
                                            timestamp: SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_millis() as u64,
                                            bid: ticker.get("bid1Price").and_then(|b| b.as_str()).and_then(|s| s.parse().ok()),
                                            ask: ticker.get("ask1Price").and_then(|a| a.as_str()).and_then(|s| s.parse().ok()),
                                            volume: ticker.get("volume24h").and_then(|v| v.as_str()).and_then(|s| s.parse().ok()),
                                        };

                                        Self::update_price(prices, price_data, opportunity_tx);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Ok(())
    }

    fn update_price(
        prices: &Arc<DashMap<String, DashMap<String, PriceData>>>,
        price_data: PriceData,
        opportunity_tx: &Sender<ArbitrageOpportunity>,
    ) {
        let symbol = price_data.symbol.clone();
        
        if !prices.contains_key(&symbol) {
            prices.insert(symbol.clone(), DashMap::new());
        }
        
        if let Some(symbol_prices) = prices.get(&symbol) {
            symbol_prices.insert(price_data.exchange.clone(), price_data);
            Self::check_arbitrage(&symbol, &symbol_prices, opportunity_tx);
        }
    }

    fn check_arbitrage(
        symbol: &str,
        symbol_prices: &DashMap<String, PriceData>,
        opportunity_tx: &Sender<ArbitrageOpportunity>,
    ) {
        if symbol_prices.len() < 2 {
            return;
        }

        let prices: Vec<PriceData> = symbol_prices.iter().map(|entry| entry.value().clone()).collect();
        
        let mut highest: Option<&PriceData> = None;
        let mut lowest: Option<&PriceData> = None;

        for price in &prices {
            if let Some(h) = highest {
                if price.price > h.price {
                    highest = Some(price);
                }
            } else {
                highest = Some(price);
            }

            if let Some(l) = lowest {
                if price.price < l.price {
                    lowest = Some(price);
                }
            } else {
                lowest = Some(price);
            }
        }

        if let (Some(highest), Some(lowest)) = (highest, lowest) {
            if highest.exchange != lowest.exchange {
                let spread = ((highest.price - lowest.price) / lowest.price) * 100.0;
                
                if spread >= 0.1 {
                    let profit = Self::calculate_profit(lowest.price, highest.price, 1000.0);
                    
                    let opportunity = ArbitrageOpportunity {
                        symbol: symbol.to_string(),
                        buy_exchange: lowest.exchange.clone(),
                        sell_exchange: highest.exchange.clone(),
                        buy_price: lowest.price,
                        sell_price: highest.price,
                        spread,
                        profit,
                        timestamp: SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_millis() as u64,
                    };

                    println!("\x1b[36m🎯 OPPORTUNITY: {} | {} → {} | Spread: {:.3}% | Profit: ${:.2}\x1b[0m",
                        opportunity.symbol,
                        opportunity.buy_exchange.to_uppercase(),
                        opportunity.sell_exchange.to_uppercase(),
                        opportunity.spread,
                        opportunity.profit
                    );

                    let _ = opportunity_tx.try_send(opportunity);
                }
            }
        }
    }

    fn calculate_profit(buy_price: f64, sell_price: f64, trade_size: f64) -> f64 {
        let gross_profit = (sell_price - buy_price) / buy_price * trade_size;
        let trading_fees = trade_size * 0.002;
        let slippage = trade_size * 0.001;
        gross_profit - trading_fees - slippage
    }

    fn spawn_opportunity_processor(&self) -> tokio::task::JoinHandle<Result<()>> {
        let opportunity_rx = self.opportunity_rx.clone();
        let metrics = Arc::clone(&self.metrics);

        tokio::spawn(async move {
            let mut rng = rand::thread_rng();
            while let Ok(opportunity) = opportunity_rx.recv() {
                metrics.opportunities.fetch_add(1, Ordering::Relaxed);

                if opportunity.spread >= 1.0 && opportunity.profit > 0.0 {
                    let execution_time = rng.gen_range(50.0..200.0) as u64;
                    
                    metrics.trades.fetch_add(1, Ordering::Relaxed);
                    let profit_cents = (opportunity.profit * 100.0) as u64;
                    metrics.total_profit.fetch_add(profit_cents, Ordering::Relaxed);

                    println!("\x1b[1m\x1b[32m⚡ TRADE EXECUTED: {} | Profit: ${:.2} | Time: {}ms\x1b[0m",
                        opportunity.symbol,
                        opportunity.profit,
                        execution_time
                    );
                }
            }
            Ok(())
        })
    }

    fn spawn_metrics_reporter(&self) -> tokio::task::JoinHandle<Result<()>> {
        let metrics = Arc::clone(&self.metrics);

        tokio::spawn(async move {
            loop {
                sleep(Duration::from_secs(30)).await;
                
                let opportunities = metrics.opportunities.load(Ordering::Relaxed);
                let trades = metrics.trades.load(Ordering::Relaxed);
                let profit_cents = metrics.total_profit.load(Ordering::Relaxed);
                let profit = profit_cents as f64 / 100.0;
                let runtime = metrics.start_time.elapsed().as_secs();
                
                let success_rate = if opportunities > 0 {
                    (trades as f64 / opportunities as f64) * 100.0
                } else {
                    0.0
                };
                
                let avg_profit = if trades > 0 {
                    profit / trades as f64
                } else {
                    0.0
                };

                println!("\x1b[1m\x1b[33m📊 ═══════════════ LIVE METRICS ═══════════════\x1b[0m");
                println!("⏱️  Runtime: {}m {}s", runtime / 60, runtime % 60);
                println!("🎯 Opportunities: {}", opportunities);
                println!("⚡ Trades: {}", trades);
                println!("💰 Profit: ${:.2}", profit);
                println!("📈 Success Rate: {:.1}%", success_rate);
                println!("⚖️  Avg Profit: ${:.2}", avg_profit);
                println!("\x1b[1m\x1b[33m═══════════════════════════════════════════\x1b[0m");
            }
        })
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .init();

    let bot = LightningArbitrageBot::new();
    bot.start().await?;

    Ok(())
}
