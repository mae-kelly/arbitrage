use std::collections::{HashMap, HashSet};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoinInfo {
    pub symbol: String,
    pub name: String,
    pub market_cap_rank: Option<u32>,
    pub market_cap_usd: Option<f64>,
    pub daily_volume_usd: Option<f64>,
    pub price_usd: Option<f64>,
    pub exchanges: Vec<String>,
    pub pairs: Vec<String>, // USDT, USD, BTC, ETH pairs
    pub is_defi_token: bool,
    pub is_stablecoin: bool,
    pub min_arbitrage_size_usd: f64,
}

pub struct MassiveCoinDatabase {
    coins: HashMap<String, CoinInfo>,
    top_coins: Vec<String>, // Top 100 by market cap
    trending_coins: Vec<String>, // Recently pumping
    defi_coins: Vec<String>,
    stable_coins: Vec<String>,
    exchange_specific_coins: HashMap<String, Vec<String>>,
}

impl MassiveCoinDatabase {
    pub fn new() -> Self {
        let mut db = Self {
            coins: HashMap::new(),
            top_coins: Vec::new(),
            trending_coins: Vec::new(),
            defi_coins: Vec::new(),
            stable_coins: Vec::new(),
            exchange_specific_coins: HashMap::new(),
        };
        
        db.initialize_massive_coin_list();
        db
    }
    
    fn initialize_massive_coin_list(&mut self) {
        // TOP 100 MARKET CAP COINS
        let top_100_coins = vec![
            ("BTC", "Bitcoin", 1, vec!["coinbase", "kraken", "gemini", "bitstamp", "kucoin", "mexc", "gate_io"]),
            ("ETH", "Ethereum", 2, vec!["coinbase", "kraken", "gemini", "bitstamp", "kucoin", "mexc", "gate_io"]),
            ("USDT", "Tether", 3, vec!["kucoin", "mexc", "gate_io", "bitget", "bitmart"]),
            ("BNB", "BNB", 4, vec!["kucoin", "mexc", "gate_io", "bitget"]),
            ("SOL", "Solana", 5, vec!["coinbase", "kraken", "kucoin", "mexc", "gate_io", "crypto_com"]),
            ("USDC", "USD Coin", 6, vec!["coinbase", "kraken", "gemini", "kucoin", "mexc"]),
            ("XRP", "XRP", 7, vec!["kraken", "bitstamp", "kucoin", "mexc", "gate_io"]),
            ("LUNA", "Terra Luna", 8, vec!["kucoin", "mexc", "gate_io", "bitget"]),
            ("ADA", "Cardano", 9, vec!["coinbase", "kraken", "kucoin", "mexc", "gate_io", "crypto_com"]),
            ("AVAX", "Avalanche", 10, vec!["coinbase", "kraken", "kucoin", "mexc", "gate_io"]),
            ("DOT", "Polkadot", 11, vec!["coinbase", "kraken", "kucoin", "mexc", "gate_io"]),
            ("DOGE", "Dogecoin", 12, vec!["coinbase", "kraken", "kucoin", "mexc", "gate_io"]),
            ("MATIC", "Polygon", 13, vec!["coinbase", "kraken", "kucoin", "mexc", "gate_io"]),
            ("SHIB", "Shiba Inu", 14, vec!["coinbase", "kucoin", "mexc", "gate_io", "crypto_com"]),
            ("LTC", "Litecoin", 15, vec!["coinbase", "kraken", "gemini", "bitstamp", "kucoin"]),
            ("ATOM", "Cosmos", 16, vec!["coinbase", "kraken", "kucoin", "mexc", "gate_io"]),
            ("NEAR", "NEAR Protocol", 17, vec!["coinbase", "kucoin", "mexc", "gate_io", "bitget"]),
            ("BCH", "Bitcoin Cash", 18, vec!["coinbase", "kraken", "gemini", "kucoin", "mexc"]),
            ("LINK", "Chainlink", 19, vec!["coinbase", "kraken", "gemini", "kucoin", "mexc"]),
            ("UNI", "Uniswap", 20, vec!["coinbase", "kraken", "kucoin", "mexc", "gate_io"]),
            
            // More top coins (21-50)
            ("FTM", "Fantom", 21, vec!["kucoin", "mexc", "gate_io", "bitget"]),
            ("ALGO", "Algorand", 22, vec!["coinbase", "kraken", "kucoin", "mexc"]),
            ("VET", "VeChain", 23, vec!["kucoin", "mexc", "gate_io", "bitget"]),
            ("ICP", "Internet Computer", 24, vec!["coinbase", "kucoin", "mexc", "gate_io"]),
            ("XLM", "Stellar", 25, vec!["coinbase", "kraken", "kucoin", "mexc"]),
            ("HBAR", "Hedera", 26, vec!["kucoin", "mexc", "gate_io", "bitget"]),
            ("FIL", "Filecoin", 27, vec!["coinbase", "kraken", "kucoin", "mexc"]),
            ("ETC", "Ethereum Classic", 28, vec!["coinbase", "kraken", "kucoin", "mexc"]),
            ("XMR", "Monero", 29, vec!["kraken", "kucoin", "mexc", "gate_io"]),
            ("THETA", "Theta Network", 30, vec!["kucoin", "mexc", "gate_io", "bitget"]),
            ("AAVE", "Aave", 31, vec!["coinbase", "kraken", "kucoin", "mexc"]),
            ("EOS", "EOS", 32, vec!["coinbase", "kraken", "kucoin", "mexc"]),
            ("XTZ", "Tezos", 33, vec!["coinbase", "kraken", "kucoin", "mexc"]),
            ("EGLD", "MultiversX", 34, vec!["kucoin", "mexc", "gate_io", "bitget"]),
            ("MANA", "Decentraland", 35, vec!["coinbase", "kucoin", "mexc", "gate_io"]),
            ("SAND", "The Sandbox", 36, vec!["coinbase", "kucoin", "mexc", "gate_io"]),
            ("AXS", "Axie Infinity", 37, vec!["coinbase", "kucoin", "mexc", "gate_io"]),
            ("CAKE", "PancakeSwap", 38, vec!["kucoin", "mexc", "gate_io", "bitget"]),
            ("KCS", "KuCoin Shares", 39, vec!["kucoin"]),
            ("GRT", "The Graph", 40, vec!["coinbase", "kraken", "kucoin", "mexc"]),
            
            // DeFi Tokens (50-100)
            ("SUSHI", "SushiSwap", 50, vec!["coinbase", "kraken", "kucoin", "mexc"]),
            ("CRV", "Curve DAO Token", 51, vec!["coinbase", "kucoin", "mexc", "gate_io"]),
            ("YFI", "yearn.finance", 52, vec!["coinbase", "kraken", "kucoin", "mexc"]),
            ("COMP", "Compound", 53, vec!["coinbase", "kraken", "kucoin", "mexc"]),
            ("MKR", "Maker", 54, vec!["coinbase", "kraken", "kucoin", "mexc"]),
            ("SNX", "Synthetix", 55, vec!["coinbase", "kucoin", "mexc", "gate_io"]),
            ("BAL", "Balancer", 56, vec!["coinbase", "kucoin", "mexc", "gate_io"]),
            ("1INCH", "1inch Network", 57, vec!["coinbase", "kucoin", "mexc", "gate_io"]),
            ("LRC", "Loopring", 58, vec!["coinbase", "kucoin", "mexc", "gate_io"]),
            ("ALPHA", "Alpha Finance Lab", 59, vec!["kucoin", "mexc", "gate_io", "bitget"]),
        ];
        
        // Add top coins
        for (symbol, name, rank, exchanges) in top_100_coins {
            let coin_info = CoinInfo {
                symbol: symbol.to_string(),
                name: name.to_string(),
                market_cap_rank: Some(rank),
                market_cap_usd: None, // Would be fetched in real-time
                daily_volume_usd: None,
                price_usd: None,
                exchanges: exchanges.iter().map(|s| s.to_string()).collect(),
                pairs: vec!["USDT".to_string(), "USD".to_string(), "BTC".to_string()],
                is_defi_token: matches!(symbol, "UNI" | "SUSHI" | "AAVE" | "COMP" | "MKR" | "SNX" | "CRV" | "YFI" | "BAL" | "1INCH" | "LRC"),
                is_stablecoin: matches!(symbol, "USDT" | "USDC" | "DAI" | "BUSD"),
                min_arbitrage_size_usd: if rank <= 10 { 1000.0 } else if rank <= 50 { 500.0 } else { 100.0 },
            };
            
            self.coins.insert(symbol.to_string(), coin_info);
            if rank <= 100 {
                self.top_coins.push(symbol.to_string());
            }
        }
        
        // TRENDING/MEME COINS (High volatility = More arbitrage opportunities)
        let trending_meme_coins = vec![
            ("PEPE", "Pepe", vec!["kucoin", "mexc", "gate_io", "bitget"]),
            ("FLOKI", "Floki Inu", vec!["kucoin", "mexc", "gate_io", "bitget"]),
            ("BONK", "Bonk", vec!["kucoin", "mexc", "gate_io"]),
            ("WIF", "dogwifhat", vec!["kucoin", "mexc", "gate_io"]),
            ("BOME", "BOOK OF MEME", vec!["kucoin", "mexc", "gate_io"]),
            ("SLERF", "Slerf", vec!["mexc", "gate_io"]),
            ("MYRO", "Myro", vec!["mexc", "gate_io", "bitget"]),
            ("POPCAT", "Popcat", vec!["mexc", "gate_io"]),
            ("BRETT", "Brett", vec!["mexc", "gate_io"]),
            ("MEW", "cat in a dogs world", vec!["mexc", "gate_io"]),
        ];
        
        for (symbol, name, exchanges) in trending_meme_coins {
            let coin_info = CoinInfo {
                symbol: symbol.to_string(),
                name: name.to_string(),
                market_cap_rank: None,
                market_cap_usd: None,
                daily_volume_usd: None,
                price_usd: None,
                exchanges: exchanges.iter().map(|s| s.to_string()).collect(),
                pairs: vec!["USDT".to_string()],
                is_defi_token: false,
                is_stablecoin: false,
                min_arbitrage_size_usd: 50.0, // Smaller trades for meme coins
            };
            
            self.coins.insert(symbol.to_string(), coin_info);
            self.trending_coins.push(symbol.to_string());
        }
        
        // EXCHANGE-SPECIFIC TOKENS (Often have big spreads)
        let kucoin_tokens = vec!["KCS", "LOKI", "MVL", "RMRK", "TLOS"];
        let mexc_tokens = vec!["MX", "HEART", "TABOO", "NFTB", "LABS"];
        let gate_tokens = vec!["GT", "BGB", "TRADE", "NEER", "AIOZ"];
        
        for token in kucoin_tokens {
            if !self.coins.contains_key(token) {
                let coin_info = CoinInfo {
                    symbol: token.to_string(),
                    name: format!("{} Token", token),
                    market_cap_rank: None,
                    market_cap_usd: None,
                    daily_volume_usd: None,
                    price_usd: None,
                    exchanges: vec!["kucoin".to_string()],
                    pairs: vec!["USDT".to_string(), "BTC".to_string()],
                    is_defi_token: false,
                    is_stablecoin: false,
                    min_arbitrage_size_usd: 100.0,
                };
                self.coins.insert(token.to_string(), coin_info);
            }
        }
        
        // Set up categories
        self.stable_coins = vec!["USDT", "USDC", "DAI", "BUSD", "FRAX", "TUSD", "USDP"].iter().map(|s| s.to_string()).collect();
        self.defi_coins = vec!["UNI", "SUSHI", "AAVE", "COMP", "MKR", "SNX", "CRV", "YFI", "BAL", "1INCH", "LRC"].iter().map(|s| s.to_string()).collect();
    }
    
    pub fn get_all_supported_coins(&self) -> Vec<String> {
        self.coins.keys().cloned().collect()
    }
    
    pub fn get_coins_by_exchange(&self, exchange: &str) -> Vec<String> {
        self.coins
            .iter()
            .filter(|(_, info)| info.exchanges.contains(&exchange.to_string()))
            .map(|(symbol, _)| symbol.clone())
            .collect()
    }
    
    pub fn get_arbitrage_pairs(&self, min_exchanges: usize) -> Vec<String> {
        self.coins
            .iter()
            .filter(|(_, info)| info.exchanges.len() >= min_exchanges)
            .map(|(symbol, _)| symbol.clone())
            .collect()
    }
    
    pub fn get_high_volatility_coins(&self) -> Vec<String> {
        // Trending + meme coins have highest volatility
        let mut high_vol = self.trending_coins.clone();
        
        // Add some established but volatile coins
        high_vol.extend(vec![
            "SHIB".to_string(), "DOGE".to_string(), "AXS".to_string(),
            "MANA".to_string(), "SAND".to_string(), "FTM".to_string()
        ]);
        
        high_vol
    }
    
    pub fn get_stable_arbitrage_coins(&self) -> Vec<String> {
        // Top 20 coins - more stable, less slippage
        self.top_coins.iter().take(20).cloned().collect()
    }
    
    pub fn get_cross_exchange_opportunities(&self) -> Vec<(String, Vec<String>)> {
        let mut opportunities = Vec::new();
        
        for (symbol, info) in &self.coins {
            if info.exchanges.len() >= 2 {
                opportunities.push((symbol.clone(), info.exchanges.clone()));
            }
        }
        
        // Sort by number of exchanges (more exchanges = more arbitrage potential)
        opportunities.sort_by(|a, b| b.1.len().cmp(&a.1.len()));
        opportunities
    }
    
    pub fn get_coin_info(&self, symbol: &str) -> Option<&CoinInfo> {
        self.coins.get(symbol)
    }
    
    pub fn get_total_coin_count(&self) -> usize {
        self.coins.len()
    }
    
    pub fn get_total_arbitrage_pairs(&self) -> usize {
        self.coins
            .values()
            .map(|info| {
                let exchanges = info.exchanges.len();
                if exchanges >= 2 {
                    exchanges * (exchanges - 1) // All directional pairs
                } else {
                    0
                }
            })
            .sum()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_massive_coin_database() {
        let db = MassiveCoinDatabase::new();
        
        println!("Total coins supported: {}", db.get_total_coin_count());
        println!("Total arbitrage pairs: {}", db.get_total_arbitrage_pairs());
        println!("Top arbitrage coins: {:?}", db.get_arbitrage_pairs(3).iter().take(10).collect::<Vec<_>>());
        
        assert!(db.get_total_coin_count() >= 100);
        assert!(db.get_total_arbitrage_pairs() >= 500);
    }
    
    #[test]
    fn test_btc_coverage() {
        let db = MassiveCoinDatabase::new();
        let btc_info = db.get_coin_info("BTC").unwrap();
        
        println!("BTC available on: {:?}", btc_info.exchanges);
        assert!(btc_info.exchanges.len() >= 5);
    }
    
    #[test]
    fn test_high_volatility_coins() {
        let db = MassiveCoinDatabase::new();
        let volatile_coins = db.get_high_volatility_coins();
        
        println!("High volatility coins: {:?}", volatile_coins);
        assert!(volatile_coins.len() >= 10);
    }
}
