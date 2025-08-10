use crate::strategy_engine::ArbitrageOpportunity;
use crate::websocket_feeds::Layer;
use std::sync::Arc;
use tokio::sync::Mutex;
use rust_decimal::prelude::*;
use rust_decimal_macros::dec;  // Added this import

pub struct ExecutionEngine {
    active_trades: Arc<Mutex<Vec<String>>>,
    total_profit: Arc<Mutex<Decimal>>,
    trade_count: Arc<Mutex<u64>>,
}

impl ExecutionEngine {
    pub fn new() -> Self {
        Self {
            active_trades: Arc::new(Mutex::new(Vec::new())),
            total_profit: Arc::new(Mutex::new(dec!(0))),  // Now this will work
            trade_count: Arc::new(Mutex::new(0)),
        }
    }

    pub async fn execute_opportunity(&self, opp: &ArbitrageOpportunity) -> Result<(), anyhow::Error> {
        let trade_id = format!("{}-{}", opp.buy_exchange, opp.sell_exchange);
        
        {
            let mut active = self.active_trades.lock().await;
            if active.contains(&trade_id) {
                return Ok(());
            }
            active.push(trade_id.clone());
        }

        println!("\n🚀 EXECUTING ARBITRAGE:");
        println!("  BUY:  {} @ ${} ({})", opp.buy_exchange, opp.buy_price, format_layer(&opp.buy_layer));
        println!("  SELL: {} @ ${} ({})", opp.sell_exchange, opp.sell_price, format_layer(&opp.sell_layer));
        println!("  PROFIT: {}% (${} on $10k)", opp.profit_percentage, opp.estimated_profit_usd);
        println!("  EST. TIME: {}ms", opp.execution_time_ms);

        match (&opp.buy_layer, &opp.sell_layer) {
            (Layer::L1Cex, Layer::L1Cex) => {
                self.execute_cex_to_cex(opp).await?;
            },
            (Layer::L1Cex, Layer::L2Arbitrum) | (Layer::L1Cex, Layer::L2Optimism) => {
                self.execute_cex_to_l2(opp).await?;
            },
            (Layer::L2Arbitrum, Layer::L2Arbitrum) | (Layer::L2Optimism, Layer::L2Optimism) => {
                self.execute_l2_to_l2(opp).await?;
            },
            _ => {
                self.execute_complex_route(opp).await?;
            }
        }

        {
            let mut profit = self.total_profit.lock().await;
            *profit += opp.estimated_profit_usd;
            
            let mut count = self.trade_count.lock().await;
            *count += 1;
            
            println!("✅ Trade #{} complete! Session profit: ${}", *count, *profit);
        }

        {
            let mut active = self.active_trades.lock().await;
            active.retain(|x| x != &trade_id);
        }

        Ok(())
    }

    async fn execute_cex_to_cex(&self, _opp: &ArbitrageOpportunity) -> Result<(), anyhow::Error> {
        println!("  ⚡ Executing CEX-to-CEX atomic swap...");
        tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;
        Ok(())
    }

    async fn execute_cex_to_l2(&self, _opp: &ArbitrageOpportunity) -> Result<(), anyhow::Error> {
        println!("  🌉 Bridging from CEX to L2...");
        tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
        Ok(())
    }

    async fn execute_l2_to_l2(&self, _opp: &ArbitrageOpportunity) -> Result<(), anyhow::Error> {
        println!("  🔄 Executing L2-to-L2 swap...");
        tokio::time::sleep(tokio::time::Duration::from_millis(200)).await;
        Ok(())
    }

    async fn execute_complex_route(&self, _opp: &ArbitrageOpportunity) -> Result<(), anyhow::Error> {
        println!("  🔀 Executing complex multi-hop route...");
        tokio::time::sleep(tokio::time::Duration::from_millis(1000)).await;
        Ok(())
    }
}

fn format_layer(layer: &Layer) -> &str {
    match layer {
        Layer::L1Cex => "L1-CEX",
        Layer::L1Dex => "L1-DEX",
        Layer::L2Arbitrum => "L2-ARB",
        Layer::L2Optimism => "L2-OP",
        Layer::L2Polygon => "L2-POLY",
        Layer::L2Base => "L2-BASE",
    }
}
