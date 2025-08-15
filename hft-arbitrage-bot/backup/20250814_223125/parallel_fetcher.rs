use tokio::task::JoinSet;
use reqwest::Client;
use std::time::Duration;
use rayon::prelude::*;

pub struct MassiveFetcher {
    client: Client,
    us_exchanges: Vec<String>,
    top_coins: Vec<String>,
}

impl MassiveFetcher {
    pub fn new() -> Self {
        let us_exchanges = vec![
            "coinbase".to_string(), "kraken".to_string(), "gemini".to_string(),
            "bittrex".to_string(), "crypto_com".to_string(), "kucoin".to_string(),
            "gate_io".to_string(), "mexc".to_string(), "bitget".to_string(),
            "bitmart".to_string(), "lbank".to_string(), "probit".to_string()
        ];

        let top_coins = vec![
            "BTC".to_string(), "ETH".to_string(), "ADA".to_string(), "SOL".to_string(),
            "MATIC".to_string(), "LINK".to_string(), "UNI".to_string(), "AVAX".to_string(),
            "DOT".to_string(), "ATOM".to_string(), "XLM".to_string(), "VET".to_string(),
            "AAVE".to_string(), "MKR".to_string(), "COMP".to_string(), "YFI".to_string()
        ];

        Self {
            client: Client::builder()
                .timeout(Duration::from_secs(3))
                .build()
                .expect("Failed to create client"),
            us_exchanges,
            top_coins,
        }
    }

    pub async fn fetch_all_prices_parallel(&self) -> Vec<(String, String, f64, f64)> {
        let mut tasks = JoinSet::new();
        
        // Launch 200+ parallel requests
        for exchange in &self.us_exchanges {
            for coin in &self.top_coins {
                let client = self.client.clone();
                let exchange = exchange.clone();
                let coin = coin.clone();
                
                tasks.spawn(async move {
                    Self::fetch_single_price(client, exchange, coin).await
                });
            }
        }

        let mut results = Vec::new();
        while let Some(result) = tasks.join_next().await {
            if let Ok(Some(price_data)) = result {
                results.push(price_data);
            }
        }

        results
    }

    async fn fetch_single_price(client: Client, exchange: String, coin: String) -> Option<(String, String, f64, f64)> {
        match exchange.as_str() {
            "coinbase" => Self::fetch_coinbase(&client, &coin).await,
            "kraken" => Self::fetch_kraken(&client, &coin).await,
            "kucoin" => Self::fetch_kucoin(&client, &coin).await,
            _ => None,
        }
    }

    async fn fetch_coinbase(client: &Client, coin: &str) -> Option<(String, String, f64, f64)> {
        let symbol = format!("{}-USD", coin);
        let url = format!("https://api.exchange.coinbase.com/products/{}/ticker", symbol);
        
        if let Ok(response) = client.get(&url).send().await {
            if let Ok(data) = response.json::<serde_json::Value>().await {
                let bid = data["bid"].as_str()?.parse().ok()?;
                let ask = data["ask"].as_str()?.parse().ok()?;
                return Some(("coinbase".to_string(), coin.to_string(), bid, ask));
            }
        }
        None
    }

    async fn fetch_kraken(client: &Client, coin: &str) -> Option<(String, String, f64, f64)> {
        let symbol = match coin {
            "BTC" => "XXBTZUSD",
            "ETH" => "XETHZUSD",
            _ => return None,
        };
        
        let url = format!("https://api.kraken.com/0/public/Ticker?pair={}", symbol);
        
        if let Ok(response) = client.get(&url).send().await {
            if let Ok(data) = response.json::<serde_json::Value>().await {
                if let Some(result) = data["result"].as_object() {
                    if let Some((_, ticker)) = result.iter().next() {
                        let bid = ticker["b"][0].as_str()?.parse().ok()?;
                        let ask = ticker["a"][0].as_str()?.parse().ok()?;
                        return Some(("kraken".to_string(), coin.to_string(), bid, ask));
                    }
                }
            }
        }
        None
    }

    async fn fetch_kucoin(client: &Client, coin: &str) -> Option<(String, String, f64, f64)> {
        let symbol = format!("{}-USDT", coin);
        let url = format!("https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={}", symbol);
        
        if let Ok(response) = client.get(&url).send().await {
            if let Ok(data) = response.json::<serde_json::Value>().await {
                if let Some(ticker) = data["data"].as_object() {
                    let bid = ticker["bestBid"].as_str()?.parse().ok()?;
                    let ask = ticker["bestAsk"].as_str()?.parse().ok()?;
                    return Some(("kucoin".to_string(), coin.to_string(), bid, ask));
                }
            }
        }
        None
    }

    pub fn find_flash_loan_opportunities(&self, prices: &[(String, String, f64, f64)]) -> Vec<String> {
        prices.par_iter()
            .filter_map(|(exchange, coin, bid, ask)| {
                // Find arbitrage opportunities that justify flash loans
                for (other_exchange, other_coin, other_bid, other_ask) in prices {
                    if exchange != other_exchange && coin == other_coin {
                        if other_bid > ask && ask > &0.0 {
                            let profit_pct = ((other_bid - ask) / ask) * 100.0;
                            if profit_pct > 0.1 { // >0.1% for flash loan profitability
                                return Some(format!(
                                    "FLASH LOAN: {} | Buy {} @ ${:.2} -> Sell {} @ ${:.2} = {:.3}% profit",
                                    coin, exchange, ask, other_exchange, other_bid, profit_pct
                                ));
                            }
                        }
                    }
                }
                None
            })
            .collect()
    }
}
