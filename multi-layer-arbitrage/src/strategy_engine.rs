use crate::websocket_feeds::{PriceUpdate, Layer};
use std::sync::Arc;
use dashmap::DashMap;
use rust_decimal::prelude::*;
use rust_decimal_macros::dec;

#[derive(Clone)]  // Only one Clone derive
pub struct ArbitrageOpportunity {
    pub buy_exchange: String,
    pub sell_exchange: String,
    pub buy_price: Decimal,
    pub sell_price: Decimal,
    pub profit_percentage: Decimal,
    pub estimated_profit_usd: Decimal,
    pub buy_layer: Layer,
    pub sell_layer: Layer,
    pub execution_time_ms: u64,
}

pub struct StrategyEngine {
    opportunities: Arc<DashMap<String, ArbitrageOpportunity>>,
    min_profit_threshold: Decimal,
}

impl StrategyEngine {
    pub fn new() -> Self {
        Self {
            opportunities: Arc::new(DashMap::new()),
            min_profit_threshold: dec!(0.0001), // Lowered to 0.01% to see more opportunities
        }
    }

    pub fn analyze_prices(&self, prices: &DashMap<String, PriceUpdate>) -> Vec<ArbitrageOpportunity> {
        let mut opportunities = Vec::new();
        let price_snapshot: Vec<_> = prices.iter().map(|p| p.clone()).collect();
        
        // Only process if we have at least 2 price sources
        if price_snapshot.len() < 2 {
            return opportunities;
        }
        
        for i in 0..price_snapshot.len() {
            for j in 0..price_snapshot.len() {
                if i == j { continue; }
                
                let price1 = &price_snapshot[i];
                let price2 = &price_snapshot[j];
                
                // Buy from exchange 1 (at ask), sell to exchange 2 (at bid)
                let buy_price = Decimal::from_f64(price1.ask).unwrap_or(dec!(0));
                let sell_price = Decimal::from_f64(price2.bid).unwrap_or(dec!(0));
                
                if buy_price > dec!(0) && sell_price > dec!(0) && sell_price > buy_price {
                    let gross_profit_pct = (sell_price - buy_price) / buy_price;
                    let total_fee = self.calculate_fees(&price1.layer, &price2.layer);
                    let net_profit = gross_profit_pct - total_fee;
                    
                    // Show opportunities even with small profits
                    if net_profit > self.min_profit_threshold {
                        let execution_time = self.estimate_execution_time(&price1.layer, &price2.layer);
                        
                        opportunities.push(ArbitrageOpportunity {
                            buy_exchange: price1.exchange.clone(),
                            sell_exchange: price2.exchange.clone(),
                            buy_price,
                            sell_price,
                            profit_percentage: net_profit * dec!(100),
                            estimated_profit_usd: net_profit * dec!(10000),
                            buy_layer: price1.layer.clone(),
                            sell_layer: price2.layer.clone(),
                            execution_time_ms: execution_time,
                        });
                    }
                }
            }
        }
        
        // Sort by profit
        opportunities.sort_by(|a, b| b.profit_percentage.cmp(&a.profit_percentage));
        opportunities
    }

    fn calculate_fees(&self, _buy_layer: &Layer, _sell_layer: &Layer) -> Decimal {
        dec!(0.002) // 0.2% total fees (simplified)
    }

    fn estimate_execution_time(&self, _buy_layer: &Layer, _sell_layer: &Layer) -> u64 {
        100 // 100ms for all trades (simplified)
    }
}
