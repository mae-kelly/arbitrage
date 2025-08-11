mod us_exchanges;
mod massive_coins;
mod flash_loans;
mod ultra_engine;
mod parallel_fetcher;
mod perf_monitor;

use anyhow::Result;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::time::sleep;
use tracing::{info, warn};

use crate::flash_loans::FlashLoanEngine;
use crate::ultra_engine::UltraEngine;
use crate::parallel_fetcher::MassiveFetcher;
use crate::perf_monitor::PerformanceMonitor;

struct UltraFastArbitrageBot {
    flash_engine: Arc<FlashLoanEngine>,
    ultra_engine: Arc<UltraEngine>,
    massive_fetcher: Arc<MassiveFetcher>,
    perf_monitor: Arc<PerformanceMonitor>,
}

impl UltraFastArbitrageBot {
    fn new() -> Self {
        Self {
            flash_engine: Arc::new(FlashLoanEngine::new()),
            ultra_engine: Arc::new(UltraEngine::new(1000, 50)), // 1000 coins, 50 exchanges
            massive_fetcher: Arc::new(MassiveFetcher::new()),
            perf_monitor: Arc::new(PerformanceMonitor::new()),
        }
    }

    async fn run(&self) -> Result<()> {
        info!("🚀 ULTRA-FAST FLASH LOAN ARBITRAGE BOT STARTED");
        info!("⚡ Target: <100μs scans, 1000+ coins, 50+ US exchanges");
        info!("💰 Flash loan providers: Aave, Balancer, dYdX");
        
        let mut scan_count = 0u64;

        loop {
            let cycle_start = Instant::now();
            scan_count += 1;

            // PHASE 1: Massive parallel price fetching
            info!("🔥 Fetching prices from 50+ exchanges for 1000+ coins...");
            let fetch_start = Instant::now();
            let all_prices = self.massive_fetcher.fetch_all_prices_parallel().await;
            let fetch_time = fetch_start.elapsed();
            
            info!("✅ Fetched {} prices in {}ms", all_prices.len(), fetch_time.as_millis());

            if !all_prices.is_empty() {
                // PHASE 2: Ultra-fast opportunity scanning
                let scan_start = Instant::now();
                let opportunities_found = self.ultra_engine.ultra_scan();
                let scan_time = scan_start.elapsed();

                // PHASE 3: Flash loan opportunity analysis
                let flash_opportunities = self.massive_fetcher.find_flash_loan_opportunities(&all_prices);
                
                let mut total_profit_potential = 0.0;
                let mut flash_loan_count = 0;

                if !flash_opportunities.is_empty() {
                    info!("💰 Found {} FLASH LOAN ARBITRAGE opportunities:", flash_opportunities.len());
                    
                    for (i, opp) in flash_opportunities.iter().take(10).enumerate() {
                        info!("   {}. {}", i + 1, opp);
                        
                        // Extract profit for tracking
                        if let Some(profit_start) = opp.find("= ") {
                            if let Some(profit_end) = opp[profit_start + 2..].find("%") {
                                if let Ok(profit_pct) = opp[profit_start + 2..profit_start + 2 + profit_end].parse::<f64>() {
                                    let estimated_profit = profit_pct * 100.0; // $10k trade
                                    total_profit_potential += estimated_profit;
                                    flash_loan_count += 1;
                                    
                                    self.perf_monitor.record_flash_loan_opportunity(estimated_profit);
                                }
                            }
                        }
                    }
                } else {
                    info!("📊 No profitable flash loan opportunities found this cycle");
                }

                // PHASE 4: Performance tracking
                self.perf_monitor.record_scan(
                    scan_time.as_nanos() as u64,
                    opportunities_found,
                    total_profit_potential
                );

                // PHASE 5: Real-time performance display
                if scan_count % 5 == 0 {
                    self.perf_monitor.print_live_stats();
                }

                let cycle_time = cycle_start.elapsed();
                info!("⚡ Complete cycle #{} in {}ms | Scan: {}μs | {} flash loans | ${:.2} profit potential",
                      scan_count, cycle_time.as_millis(), scan_time.as_micros(), 
                      flash_loan_count, total_profit_potential);

                // Performance achievements
                if scan_time.as_micros() < 100 {
                    info!("🎯 ULTRA-SPEED ACHIEVED: {}μs scan time!", scan_time.as_micros());
                }
                if flash_loan_count > 5 {
                    info!("💰 HIGH OPPORTUNITY CYCLE: {} flash loan opportunities!", flash_loan_count);
                }
            }

            // High-frequency scanning - adjust based on performance
            let sleep_time = if all_prices.len() > 100 { 
                Duration::from_millis(500) // Faster when getting good data
            } else { 
                Duration::from_secs(2) // Slower when limited data
            };
            
            sleep(sleep_time).await;
        }
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .init();

    println!("⚡ ULTRA-FAST FLASH LOAN ARBITRAGE BOT");
    println!("======================================");
    println!("🎯 Performance targets:");
    println!("   • <100μs opportunity scanning");
    println!("   • 1000+ cryptocurrencies");
    println!("   • 50+ US-legal exchanges");
    println!("   • Flash loan integration");
    println!("   • Real-time profit calculation");
    println!("");

    let bot = UltraFastArbitrageBot::new();
    bot.run().await
}
