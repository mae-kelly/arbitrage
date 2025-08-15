use crate::exchange_discovery::{ExchangeDiscovery, ExchangeInfo, SymbolFormat};
use anyhow::Result;
use reqwest::Client;
use serde_json::Value;
use std::collections::HashMap;
use tokio::time::{sleep, Duration};
use tracing::{info, debug};

#[derive(Debug, Clone)]
pub struct LivePrice {
    pub exchange: String,
    #[allow(dead_code)]
    pub symbol: String,
    pub bid: f64,
    pub ask: f64,
    pub volume: f64,
    #[allow(dead_code)]
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone)]
pub struct ArbitrageOpportunity {
    pub symbol: String,
    pub buy_exchange: String,
    pub sell_exchange: String,
    pub buy_price: f64,
    pub sell_price: f64,
    pub profit_percentage: f64,
    pub estimated_profit_usd: f64,
    pub volume_score: f64,
}

pub struct DynamicArbitrageScanner {
    client: Client,
    exchanges: Vec<ExchangeInfo>,
    price_cache: HashMap<String, HashMap<String, LivePrice>>, // exchange -> symbol -> price
    min_profit_threshold: f64,
    min_volume_usd: f64,
}

impl DynamicArbitrageScanner {
    pub fn new(exchanges: Vec<ExchangeInfo>) -> Self {
        Self {
            client: Client::builder()
                .timeout(Duration::from_secs(10))
                .build()
                .expect("Failed to create HTTP client"),
            exchanges,
            price_cache: HashMap::new(),
            min_profit_threshold: 0.3, // 0.3% minimum
            min_volume_usd: 10000.0,   // $10k minimum volume
        }
    }

    pub async fn scan_all_opportunities(&mut self) -> Result<Vec<ArbitrageOpportunity>> {
        info!("🔍 Starting massive arbitrage scan across {} exchanges...", self.exchanges.len());
        
        // Get common symbols across multiple exchanges
        let discovery = ExchangeDiscovery::new();
        let common_symbols = discovery.get_common_symbols(3); // At least 3 exchanges
        
        info!("📊 Scanning {} symbols across {} exchanges = {} price points", 
              common_symbols.len(), self.exchanges.len(), 
              common_symbols.len() * self.exchanges.len());

        // Fetch prices from all exchanges for all common symbols
        for exchange in &self.exchanges {
            self.price_cache.insert(exchange.name.clone(), HashMap::new());
            
            for symbol in &common_symbols {
                if exchange.available_symbols.contains(symbol) {
                    match self.fetch_price_from_exchange(exchange, symbol).await {
                        Ok(price) => {
                            self.price_cache
                                .get_mut(&exchange.name)
                                .unwrap()
                                .insert(symbol.clone(), price);
                        }
                        Err(e) => {
                            debug!("Failed to fetch {} from {}: {}", symbol, exchange.name, e);
                        }
                    }
                    
                    // Rate limiting
                    sleep(Duration::from_millis(exchange.rate_limit_ms)).await;
                }
            }
            
            info!("✅ {}: {} prices fetched", exchange.name.to_uppercase(), 
                  self.price_cache.get(&exchange.name).unwrap().len());
        }

        // Find arbitrage opportunities
        let opportunities = self.find_arbitrage_opportunities(&common_symbols);
        
        info!("💰 Found {} arbitrage opportunities!", opportunities.len());
        Ok(opportunities)
    }

    async fn fetch_price_from_exchange(&self, exchange: &ExchangeInfo, symbol: &str) -> Result<LivePrice> {
        let formatted_symbol = self.format_symbol_for_exchange(symbol, &exchange.symbol_format);
        let url = self.build_ticker_url(exchange, &formatted_symbol);
        
        let response = self.client.get(&url).send().await?;
        let data: Value = response.json().await?;
        
        let (bid, ask, volume) = match exchange.name.as_str() {
            "coinbase" => {
                let bid: f64 = data["bid"].as_str().unwrap_or("0").parse()?;
                let ask: f64 = data["ask"].as_str().unwrap_or("0").parse()?;
                let volume: f64 = data["volume"].as_str().unwrap_or("0").parse()?;
                (bid, ask, volume)
            }
            
            "kraken" => {
                if let Some(result) = data["result"].as_object() {
                    if let Some((_, ticker)) = result.iter().next() {
                        let bid: f64 = ticker["b"][0].as_str().unwrap_or("0").parse()?;
                        let ask: f64 = ticker["a"][0].as_str().unwrap_or("0").parse()?;
                        let volume: f64 = ticker["v"][1].as_str().unwrap_or("0").parse()?;
                        (bid, ask, volume)
                    } else {
                        (0.0, 0.0, 0.0)
                    }
                } else {
                    (0.0, 0.0, 0.0)
                }
            }
            
            "kucoin" => {
                let ticker_data = &data["data"];
                let bid: f64 = ticker_data["bestBid"].as_str().unwrap_or("0").parse()?;
                let ask: f64 = ticker_data["bestAsk"].as_str().unwrap_or("0").parse()?;
                let volume: f64 = ticker_data["size"].as_str().unwrap_or("0").parse()?;
                (bid, ask, volume)
            }
            
            _ => {
                // Generic parsing for other exchanges
                let bid: f64 = data["bid"].as_str()
                    .or_else(|| data["bestBid"].as_str())
                    .or_else(|| data["buy"].as_str())
                    .unwrap_or("0").parse().unwrap_or(0.0);
                
                let ask: f64 = data["ask"].as_str()
                    .or_else(|| data["bestAsk"].as_str())
                    .or_else(|| data["sell"].as_str())
                    .unwrap_or("0").parse().unwrap_or(0.0);
                
                let volume: f64 = data["volume"].as_str()
                    .or_else(|| data["vol"].as_str())
                    .or_else(|| data["baseVolume"].as_str())
                    .unwrap_or("0").parse().unwrap_or(0.0);
                
                (bid, ask, volume)
            }
        };

        Ok(LivePrice {
            exchange: exchange.name.clone(),
            symbol: symbol.to_string(),
            bid,
            ask,
            volume,
            timestamp: chrono::Utc::now(),
        })
    }

    fn format_symbol_for_exchange(&self, symbol: &str, format: &SymbolFormat) -> String {
        match format {
            SymbolFormat::Dash => symbol.replace("/", "-").replace("_", "-"),
            SymbolFormat::Underscore => symbol.replace("/", "_").replace("-", "_"),
            SymbolFormat::Concat => symbol.replace("/", "").replace("-", "").replace("_", ""),
            SymbolFormat::Slash => symbol.replace("-", "/").replace("_", "/"),
        }
    }

    fn build_ticker_url(&self, exchange: &ExchangeInfo, symbol: &str) -> String {
        if exchange.ticker_endpoint.contains("{}") {
            format!("{}{}", exchange.api_base, exchange.ticker_endpoint.replace("{}", symbol))
        } else {
            format!("{}{}?symbol={}", exchange.api_base, exchange.ticker_endpoint, symbol)
        }
    }

    fn find_arbitrage_opportunities(&self, symbols: &[String]) -> Vec<ArbitrageOpportunity> {
        let mut opportunities = Vec::new();

        for symbol in symbols {
            let mut prices_for_symbol = Vec::new();
            
            // Collect all prices for this symbol
            for (_exchange_name, exchange_prices) in &self.price_cache {  // Prefix with underscore to indicate intentional non-use
                if let Some(price) = exchange_prices.get(symbol) {
                    if price.bid > 0.0 && price.ask > 0.0 && price.volume * price.ask >= self.min_volume_usd {
                        prices_for_symbol.push(price);
                    }
                }
            }

            // Find arbitrage opportunities for this symbol
            for i in 0..prices_for_symbol.len() {
                for j in (i + 1)..prices_for_symbol.len() {
                    let price1 = &prices_for_symbol[i];
                    let price2 = &prices_for_symbol[j];

                    // Check both directions
                    if price2.bid > price1.ask {
                        let profit_pct = ((price2.bid - price1.ask) / price1.ask) * 100.0;
                        if profit_pct >= self.min_profit_threshold {
                            opportunities.push(ArbitrageOpportunity {
                                symbol: symbol.clone(),
                                buy_exchange: price1.exchange.clone(),
                                sell_exchange: price2.exchange.clone(),
                                buy_price: price1.ask,
                                sell_price: price2.bid,
                                profit_percentage: profit_pct,
                                estimated_profit_usd: (profit_pct / 100.0) * 10000.0 - 50.0, // $10k trade - fees
                                volume_score: (price1.volume * price1.ask + price2.volume * price2.bid) / 2.0,
                            });
                        }
                    }

                    if price1.bid > price2.ask {
                        let profit_pct = ((price1.bid - price2.ask) / price2.ask) * 100.0;
                        if profit_pct >= self.min_profit_threshold {
                            opportunities.push(ArbitrageOpportunity {
                                symbol: symbol.clone(),
                                buy_exchange: price2.exchange.clone(),
                                sell_exchange: price1.exchange.clone(),
                                buy_price: price2.ask,
                                sell_price: price1.bid,
                                profit_percentage: profit_pct,
                                estimated_profit_usd: (profit_pct / 100.0) * 10000.0 - 50.0,
                                volume_score: (price1.volume * price1.ask + price2.volume * price2.bid) / 2.0,
                            });
                        }
                    }
                }
            }
        }

        // Sort by profit percentage
        opportunities.sort_by(|a, b| b.profit_percentage.partial_cmp(&a.profit_percentage).unwrap());
        opportunities.into_iter().take(20).collect() // Top 20 opportunities
    }
}