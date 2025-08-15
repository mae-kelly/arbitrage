use anyhow::Result;
use std::time::Instant;
use tokio::time::{sleep, Duration};
use tracing::info;

mod exchange_discovery;
mod dynamic_arbitrage;

use exchange_discovery::ExchangeDiscovery;
use dynamic_arbitrage::DynamicArbitrageScanner;

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .init();

    println!("🌍 MASSIVE SCALE ARBITRAGE BOT");
    println!("===============================");
    println!("🎯 Discovering ALL US-legal exchanges...");
    println!("🔍 Fetching ALL available tokens...");
    println!("💰 Finding arbitrage across EVERYTHING...");
    println!("");

    // Step 1: Discover all US-legal exchanges and their tokens
    let mut discovery = ExchangeDiscovery::new();
    discovery.discover_all_us_exchanges().await?;
    
    let exchanges = discovery.get_exchanges().clone();
    let all_symbols = discovery.get_all_unique_symbols();
    let common_symbols = discovery.get_common_symbols(3);

    info!("📊 DISCOVERY COMPLETE:");
    info!("   • {} US-legal exchanges discovered", exchanges.len());
    info!("   • {} total unique symbols found", all_symbols.len());
    info!("   • {} symbols available on 3+ exchanges", common_symbols.len());
    info!("");

    // Save discovery results
    discovery.save_discovery_results("exchange_discovery.json").await?;

    // Step 2: Start massive arbitrage scanning
    let mut scanner = DynamicArbitrageScanner::new(exchanges);
    
    let mut cycle = 0;
    loop {
        cycle += 1;
        let start = Instant::now();
        
        info!("🔍 === MASSIVE SCAN #{} ===", cycle);
        
        match scanner.scan_all_opportunities().await {
            Ok(opportunities) => {
                let elapsed = start.elapsed();
                
                info!("⚡ Scan completed in {:.1}s | {} opportunities found", 
                      elapsed.as_secs_f64(), opportunities.len());

                if !opportunities.is_empty() {
                    info!("");
                    info!("💰 🚀 ARBITRAGE OPPORTUNITIES DISCOVERED! 🚀");
                    info!("==============================================");
                    
                    for (i, opp) in opportunities.iter().take(10).enumerate() {
                        info!("{}. {} ARBITRAGE", i + 1, opp.symbol);
                        info!("   📈 Buy:  {} @ ${:.6}", opp.buy_exchange.to_uppercase(), opp.buy_price);
                        info!("   📉 Sell: {} @ ${:.6}", opp.sell_exchange.to_uppercase(), opp.sell_price);
                        info!("   💵 Profit: {:.3}% | Est: ${:.2} | Volume Score: ${:.0}", 
                              opp.profit_percentage, opp.estimated_profit_usd, opp.volume_score);
                        info!("   ─────────────────────────────────────────────");
                    }
                    
                    if opportunities.len() > 10 {
                        info!("   ... and {} more opportunities!", opportunities.len() - 10);
                    }
                    
                    info!("");
                    info!("🚨 MANUAL EXECUTION REQUIRED");
                    info!("   (Auto-trading disabled for safety)");
                } else {
                    info!("📊 No profitable arbitrage found above 0.3% threshold");
                }
            }
            Err(e) => {
                info!("❌ Scan failed: {}", e);
            }
        }

        info!("");
        info!("⏰ Next massive scan in 5 minutes...");
        info!("════════════════════════════════════════════");
        info!("");
        
        // Longer intervals for massive scans to respect API limits
        sleep(Duration::from_secs(300)).await; // 5 minutes
    }
}
