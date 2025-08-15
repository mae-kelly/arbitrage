use anyhow::Result;
use reqwest::Client;
use serde_json::Value;
use std::collections::{HashMap, HashSet};
use tokio::time::{sleep, Duration};
use tracing::{info, warn, error};

#[derive(Debug, Clone)]
pub struct ExchangeInfo {
    pub name: String,
    pub api_base: String,
    pub symbols_endpoint: String,
    pub ticker_endpoint: String,
    pub symbol_format: SymbolFormat,
    pub rate_limit_ms: u64,
    pub is_us_legal: bool,
    pub available_symbols: HashSet<String>,
}

#[derive(Debug, Clone)]
pub enum SymbolFormat {
    Dash,      // BTC-USD
    Underscore, // BTC_USD  
    Concat,    // BTCUSD
    Slash,     // BTC/USD
}

pub struct ExchangeDiscovery {
    client: Client,
    us_legal_exchanges: Vec<ExchangeInfo>,
}

impl ExchangeDiscovery {
    pub fn new() -> Self {
        Self {
            client: Client::builder()
                .timeout(Duration::from_secs(30))
                .user_agent("ArbitrageBot/1.0")
                .build()
                .expect("Failed to create HTTP client"),
            us_legal_exchanges: Vec::new(),
        }
    }

    pub async fn discover_all_us_exchanges(&mut self) -> Result<()> {
        info!("🔍 Discovering all US-legal exchanges...");

        // Initialize known US-legal exchanges with their API endpoints
        let known_exchanges = vec![
            // Tier 1 - Major US-legal
            ("coinbase", "https://api.exchange.coinbase.com", "/products", "/products/{}/ticker", SymbolFormat::Dash),
            ("kraken", "https://api.kraken.com", "/0/public/AssetPairs", "/0/public/Ticker", SymbolFormat::Concat),
            ("gemini", "https://api.gemini.com", "/v1/symbols", "/v1/pubticker/{}", SymbolFormat::Concat),
            ("bitstamp", "https://www.bitstamp.net", "/api/v2/trading-pairs-info/", "/api/v2/ticker/{}/", SymbolFormat::Concat),
            
            // Tier 2 - US-accessible global exchanges
            ("kucoin", "https://api.kucoin.com", "/api/v1/symbols", "/api/v1/market/orderbook/level1", SymbolFormat::Dash),
            ("crypto_com", "https://api.crypto.com", "/v2/public/get-instruments", "/v2/public/get-ticker", SymbolFormat::Underscore),
            ("gate_io", "https://api.gateio.ws", "/api/v4/spot/currency_pairs", "/api/v4/spot/tickers", SymbolFormat::Underscore),
            ("mexc", "https://api.mexc.com", "/api/v3/exchangeInfo", "/api/v3/ticker/24hr", SymbolFormat::Concat),
            ("bitget", "https://api.bitget.com", "/api/spot/v1/public/products", "/api/spot/v1/market/ticker", SymbolFormat::Concat),
            ("bitmart", "https://api-cloud.bitmart.com", "/spot/v1/symbols", "/spot/v1/ticker", SymbolFormat::Underscore),
            ("lbank", "https://api.lbkex.com", "/v2/currencyPairs.do", "/v2/ticker/24hr.do", SymbolFormat::Underscore),
            ("probit", "https://api.probit.com", "/api/exchange/v1/market", "/api/exchange/v1/ticker", SymbolFormat::Dash),
            ("hotbit", "https://api.hotbit.io", "/v1/market.list", "/v1/market.status24h", SymbolFormat::Concat),
            
            // Tier 3 - Smaller US-accessible exchanges
            ("whitebit", "https://whitebit.com", "/api/v4/public/markets", "/api/v4/public/ticker", SymbolFormat::Underscore),
            ("xt", "https://api.xt.com", "/data/api/v1/getMarketConfig", "/data/api/v1/getTicker", SymbolFormat::Underscore),
            ("coinex", "https://api.coinex.com", "/v1/market/info", "/v1/market/ticker", SymbolFormat::Concat),
            ("bkex", "https://api.bkex.com", "/v2/common/symbols", "/v2/q/ticker/price", SymbolFormat::Underscore),
            ("digifinex", "https://openapi.digifinex.com", "/v3/markets", "/v3/ticker", SymbolFormat::Underscore),
            ("coinsbit", "https://api.coinsbit.io", "/api/v1/public/markets", "/api/v1/public/ticker", SymbolFormat::Underscore),
            ("latoken", "https://api.latoken.com", "/v2/pair", "/v2/ticker", SymbolFormat::Slash),
            ("p2pb2b", "https://api.p2pb2b.com", "/api/v2/public/markets", "/api/v2/public/ticker", SymbolFormat::Underscore),
            ("exmo", "https://api.exmo.com", "/v1.1/pair_settings", "/v1.1/ticker", SymbolFormat::Underscore),
            ("cex_io", "https://cex.io", "/api/currency_limits", "/api/ticker", SymbolFormat::Slash),
            
            // US Regional exchanges
            ("coinlist", "https://trade-api.coinlist.co", "/v1/symbols", "/v1/ticker", SymbolFormat::Dash),
            ("blockfi", "https://api.blockfi.com", "/v1/markets", "/v1/ticker", SymbolFormat::Dash),
            ("voyager", "https://api.investvoyager.com", "/v1/markets", "/v1/ticker", SymbolFormat::Dash),
            
            // DeFi/DEX with APIs
            ("uniswap_v3", "https://api.thegraph.com", "/subgraphs/name/uniswap/uniswap-v3", "", SymbolFormat::Dash),
            ("sushiswap", "https://api.thegraph.com", "/subgraphs/name/sushiswap/exchange", "", SymbolFormat::Dash),
            ("curve", "https://api.curve.fi", "/api/getPools", "", SymbolFormat::Dash),
            ("balancer", "https://api.thegraph.com", "/subgraphs/name/balancer-labs/balancer-v2", "", SymbolFormat::Dash),
            ("1inch", "https://api.1inch.io", "/v4.0/1/liquidity-sources", "", SymbolFormat::Dash),
            ("pancakeswap", "https://api.pancakeswap.info", "/api/v2/pairs", "", SymbolFormat::Dash),
        ];

        for (name, base_url, symbols_endpoint, ticker_endpoint, symbol_format) in known_exchanges {
            match self.fetch_exchange_symbols(name, base_url, symbols_endpoint, ticker_endpoint, symbol_format).await {
                Ok(symbols) => {
                    info!("✅ {}: {} symbols discovered", name.to_uppercase(), symbols.len());
                    
                    self.us_legal_exchanges.push(ExchangeInfo {
                        name: name.to_string(),
                        api_base: base_url.to_string(),
                        symbols_endpoint: symbols_endpoint.to_string(),
                        ticker_endpoint: ticker_endpoint.to_string(),
                        symbol_format,
                        rate_limit_ms: 200, // Conservative rate limiting
                        is_us_legal: true,
                        available_symbols: symbols,
                    });
                }
                Err(e) => {
                    warn!("❌ {}: Failed to fetch symbols - {}", name.to_uppercase(), e);
                }
            }
            
            // Rate limiting between exchanges
            sleep(Duration::from_millis(500)).await;
        }

        info!("🎉 Discovery complete: {} exchanges, {} total unique symbols", 
              self.us_legal_exchanges.len(), self.get_all_unique_symbols().len());

        Ok(())
    }

    async fn fetch_exchange_symbols(&self, name: &str, base_url: &str, symbols_endpoint: &str, 
                                   _ticker_endpoint: &str, _symbol_format: SymbolFormat) -> Result<HashSet<String>> {
        let mut symbols = HashSet::new();
        let url = format!("{}{}", base_url, symbols_endpoint);
        
        info!("🔍 Fetching symbols from {}: {}", name, url);

        match name {
            "coinbase" => {
                let response = self.client.get(&url).send().await?;
                let data: Value = response.json().await?;
                
                if let Some(products) = data.as_array() {
                    for product in products {
                        if let Some(id) = product["id"].as_str() {
                            symbols.insert(id.to_string());
                        }
                    }
                }
            }
            
            "kraken" => {
                let response = self.client.get(&url).send().await?;
                let data: Value = response.json().await?;
                
                if let Some(result) = data["result"].as_object() {
                    for (symbol, _info) in result {
                        symbols.insert(symbol.clone());
                    }
                }
            }
            
            "gemini" => {
                let response = self.client.get(&url).send().await?;
                let data: Value = response.json().await?;
                
                if let Some(symbol_list) = data.as_array() {
                    for symbol in symbol_list {
                        if let Some(symbol_str) = symbol.as_str() {
                            symbols.insert(symbol_str.to_string());
                        }
                    }
                }
            }
            
            "bitstamp" => {
                let response = self.client.get(&url).send().await?;
                let data: Value = response.json().await?;
                
                if let Some(pairs) = data.as_array() {
                    for pair in pairs {
                        if let Some(name) = pair["name"].as_str() {
                            symbols.insert(name.replace("/", "").to_lowercase());
                        }
                    }
                }
            }
            
            "kucoin" => {
                let response = self.client.get(&url).send().await?;
                let data: Value = response.json().await?;
                
                if let Some(symbol_data) = data["data"].as_array() {
                    for symbol_info in symbol_data {
                        if let Some(symbol) = symbol_info["symbol"].as_str() {
                            symbols.insert(symbol.to_string());
                        }
                    }
                }
            }
            
            "mexc" => {
                let response = self.client.get(&url).send().await?;
                let data: Value = response.json().await?;
                
                if let Some(symbol_data) = data["symbols"].as_array() {
                    for symbol_info in symbol_data {
                        if let Some(symbol) = symbol_info["symbol"].as_str() {
                            if symbol_info["status"].as_str() == Some("TRADING") {
                                symbols.insert(symbol.to_string());
                            }
                        }
                    }
                }
            }
            
            "gate_io" => {
                let response = self.client.get(&url).send().await?;
                let data: Value = response.json().await?;
                
                if let Some(pairs) = data.as_array() {
                    for pair in pairs {
                        if let Some(id) = pair["id"].as_str() {
                            symbols.insert(id.to_string());
                        }
                    }
                }
            }
            
            _ => {
                // Generic approach for other exchanges
                let response = self.client.get(&url).send().await?;
                let data: Value = response.json().await?;
                
                // Try to extract symbols from common JSON structures
                if let Some(array) = data.as_array() {
                    for item in array {
                        if let Some(symbol) = item["symbol"].as_str().or_else(|| item["name"].as_str()) {
                            symbols.insert(symbol.to_string());
                        }
                    }
                } else if let Some(obj) = data.as_object() {
                    for (key, _value) in obj {
                        symbols.insert(key.clone());
                    }
                }
            }
        }

        Ok(symbols)
    }

    pub fn get_all_unique_symbols(&self) -> HashSet<String> {
        let mut all_symbols = HashSet::new();
        for exchange in &self.us_legal_exchanges {
            all_symbols.extend(exchange.available_symbols.iter().cloned());
        }
        all_symbols
    }

    pub fn get_exchanges(&self) -> &Vec<ExchangeInfo> {
        &self.us_legal_exchanges
    }

    pub fn get_symbols_for_exchange(&self, exchange_name: &str) -> Option<&HashSet<String>> {
        self.us_legal_exchanges
            .iter()
            .find(|e| e.name == exchange_name)
            .map(|e| &e.available_symbols)
    }

    pub fn get_common_symbols(&self, min_exchanges: usize) -> Vec<String> {
        let mut symbol_counts: HashMap<String, usize> = HashMap::new();
        
        for exchange in &self.us_legal_exchanges {
            for symbol in &exchange.available_symbols {
                *symbol_counts.entry(symbol.clone()).or_insert(0) += 1;
            }
        }
        
        symbol_counts
            .into_iter()
            .filter(|(_, count)| *count >= min_exchanges)
            .map(|(symbol, _)| symbol)
            .collect()
    }

    pub async fn save_discovery_results(&self, filename: &str) -> Result<()> {
        let json_data = serde_json::to_string_pretty(&self.us_legal_exchanges)?;
        tokio::fs::write(filename, json_data).await?;
        info!("💾 Discovery results saved to {}", filename);
        Ok(())
    }
}
