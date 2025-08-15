use anyhow::Result;
use std::collections::HashMap;
use tracing::{info, debug};

pub struct FeeCalculator {
    exchange_fees: HashMap<String, ExchangeFees>,
}

#[derive(Debug, Clone)]
struct ExchangeFees {
    maker_fee: f64,    // Fee for limit orders
    taker_fee: f64,    // Fee for market orders
    withdrawal_fee: f64, // Withdrawal fee
    minimum_fee: f64,   // Minimum fee amount
}

impl FeeCalculator {
    pub fn new() -> Self {
        Self {
            exchange_fees: HashMap::new(),
        }
    }

    pub async fn load_real_fee_data(&mut self) -> Result<()> {
        info!("💰 Loading real exchange fee data...");

        // Load real fee structures for major exchanges
        self.load_exchange_fees();
        
        info!("✅ Loaded fee data for {} exchanges", self.exchange_fees.len());
        Ok(())
    }

    fn load_exchange_fees(&mut self) {
        // Real fee data as of 2024/2025 (check exchange websites for updates)
        
        // Tier 1 US exchanges
        self.exchange_fees.insert("coinbase".to_string(), ExchangeFees {
            maker_fee: 0.005,  // 0.5%
            taker_fee: 0.006,  // 0.6%
            withdrawal_fee: 2.0, // ~$2 for most coins
            minimum_fee: 0.99,  // $0.99 minimum
        });

        self.exchange_fees.insert("kraken".to_string(), ExchangeFees {
            maker_fee: 0.0016, // 0.16%
            taker_fee: 0.0026, // 0.26%
            withdrawal_fee: 1.5,
            minimum_fee: 0.10,
        });

        self.exchange_fees.insert("gemini".to_string(), ExchangeFees {
            maker_fee: 0.0025, // 0.25%
            taker_fee: 0.0035, // 0.35%
            withdrawal_fee: 0.0, // Free withdrawals (with conditions)
            minimum_fee: 0.99,
        });

        self.exchange_fees.insert("bitstamp".to_string(), ExchangeFees {
            maker_fee: 0.0024, // 0.24%
            taker_fee: 0.0024, // 0.24%
            withdrawal_fee: 3.0,
            minimum_fee: 0.25,
        });

        // Tier 2 exchanges
        self.exchange_fees.insert("kucoin".to_string(), ExchangeFees {
            maker_fee: 0.001,  // 0.1%
            taker_fee: 0.001,  // 0.1%
            withdrawal_fee: 1.0,
            minimum_fee: 0.10,
        });

        self.exchange_fees.insert("gate_io".to_string(), ExchangeFees {
            maker_fee: 0.002,  // 0.2%
            taker_fee: 0.002,  // 0.2%
            withdrawal_fee: 1.0,
            minimum_fee: 0.10,
        });

        self.exchange_fees.insert("mexc".to_string(), ExchangeFees {
            maker_fee: 0.002,  // 0.2%
            taker_fee: 0.002,  // 0.2%
            withdrawal_fee: 1.0,
            minimum_fee: 0.10,
        });

        self.exchange_fees.insert("bitget".to_string(), ExchangeFees {
            maker_fee: 0.001,  // 0.1%
            taker_fee: 0.001,  // 0.1%
            withdrawal_fee: 1.0,
            minimum_fee: 0.10,
        });

        // DEX fees (approximate)
        self.exchange_fees.insert("uniswap_v3".to_string(), ExchangeFees {
            maker_fee: 0.003,  // 0.3% typical pool
            taker_fee: 0.003,  // 0.3%
            withdrawal_fee: 0.0, // No withdrawal fees on DEX
            minimum_fee: 0.0,
        });

        self.exchange_fees.insert("sushiswap".to_string(), ExchangeFees {
            maker_fee: 0.003,  // 0.3%
            taker_fee: 0.003,  // 0.3%
            withdrawal_fee: 0.0,
            minimum_fee: 0.0,
        });

        debug!("📊 Loaded fee data for {} exchanges", self.exchange_fees.len());
    }

    pub fn get_trading_fee(&self, exchange: &str, trade_amount: f64) -> f64 {
        if let Some(fees) = self.exchange_fees.get(exchange) {
            // Use taker fee for arbitrage (market orders)
            let fee_amount = trade_amount * fees.taker_fee;
            fee_amount.max(fees.minimum_fee)
        } else {
            // Default fee for unknown exchanges
            debug!("⚠️  Unknown exchange {}, using default 0.25% fee", exchange);
            trade_amount * 0.0025 // 0.25% default
        }
    }

    #[allow(dead_code)]
    pub fn get_withdrawal_fee(&self, exchange: &str) -> f64 {
        if let Some(fees) = self.exchange_fees.get(exchange) {
            fees.withdrawal_fee
        } else {
            2.0 // Default $2 withdrawal fee
        }
    }

    #[allow(dead_code)]
    pub fn get_total_arbitrage_fees(&self, buy_exchange: &str, sell_exchange: &str, trade_amount: f64) -> f64 {
        let buy_fee = self.get_trading_fee(buy_exchange, trade_amount);
        let sell_fee = self.get_trading_fee(sell_exchange, trade_amount);
        let withdrawal_fee = if self.is_cross_exchange(buy_exchange, sell_exchange) {
            self.get_withdrawal_fee(buy_exchange)
        } else {
            0.0
        };
        
        buy_fee + sell_fee + withdrawal_fee
    }

    #[allow(dead_code)]
    fn is_cross_exchange(&self, exchange1: &str, exchange2: &str) -> bool {
        // Determine if we need to move funds between exchanges
        exchange1 != exchange2
    }

    #[allow(dead_code)]
    pub fn list_supported_exchanges(&self) -> Vec<String> {
        self.exchange_fees.keys().cloned().collect()
    }

    #[allow(dead_code)]
    pub fn get_exchange_info(&self, exchange: &str) -> Option<String> {
        if let Some(fees) = self.exchange_fees.get(exchange) {
            Some(format!(
                "{}: Maker {:.3}%, Taker {:.3}%, Withdrawal ${:.2}",
                exchange, 
                fees.maker_fee * 100.0, 
                fees.taker_fee * 100.0, 
                fees.withdrawal_fee
            ))
        } else {
            None
        }
    }
}
