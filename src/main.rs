use lightning_core::LightningArbitrage;
use exchanges::ExchangeRegistry;
use flash_loans::RealFlashLoanExecutor;
use rust_decimal::Decimal;
use rust_decimal::prelude::ToPrimitive;
use std::time::Duration;
use tokio::time::sleep;
use tracing::{info, warn, error};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .init();
    
    info!("⚡ LIGHTNING ARBITRAGE - REAL FLASH LOAN EXECUTION");
    info!("================================================");
    info!("🔥 REAL prices from live exchanges");
    info!("💰 REAL arbitrage opportunities");
    info!("⚡ REAL flash loan execution (display mode)");
    info!("🏦 Using Aave V3, dYdX, Uniswap V3 protocols");
    info!("");
    
    let arbitrage_system = LightningArbitrage::new();
    let price_engine = arbitrage_system.get_price_engine();
    let arbitrage_detector = arbitrage_system.get_arbitrage_detector();
    
    let exchange_registry = ExchangeRegistry::new();
    let mut flash_loan_executor = RealFlashLoanExecutor::new();
    
    info!("🚀 Starting ultra-fast arbitrage core...");
    
    tokio::spawn({
        let arbitrage_system = arbitrage_system.clone();
        async move {
            if let Err(e) = arbitrage_system.start().await {
                error!("System failed: {}", e);
            }
        }
    });
    
    sleep(Duration::from_secs(2)).await;
    
    info!("🌐 Connecting to REAL exchanges for live data...");
    info!("   📡 Binance WebSocket API");
    info!("   📡 Coinbase Advanced Trade API");
    info!("");
    
    if let Err(e) = exchange_registry.connect_all_exchanges(price_engine.clone()).await {
        error!("Failed to connect exchanges: {}", e);
        warn!("System will continue with available connections");
    }
    
    sleep(Duration::from_secs(3)).await;
    
    info!("⚡ REAL-TIME FLASH LOAN ARBITRAGE ACTIVE!");
    info!("🔍 Scanning live market for profitable opportunities...");
    info!("💡 Will EXECUTE flash loan trades when detected (display mode)");
    info!("");
    
    let (exec_stats_tx, exec_stats_rx) = tokio::sync::watch::channel((0u64, 0f64));
    
    // Real-time arbitrage execution monitor
    tokio::spawn({
        let arbitrage_detector = arbitrage_detector.clone();
        let mut flash_loan_executor = flash_loan_executor.clone();
        let exec_stats_tx = exec_stats_tx.clone();
        
        async move {
            let mut last_opportunity_count = 0;
            let mut total_executed_profit = Decimal::ZERO;
            let mut total_executions = 0u64;
            
            loop {
                sleep(Duration::from_millis(500)).await;
                
                let opportunities = arbitrage_detector.get_active_opportunities();
                
                if opportunities.len() > last_opportunity_count {
                    let new_opportunities = &opportunities[last_opportunity_count..];
                    
                    for opportunity in new_opportunities {
                        if opportunity.profit_percentage > Decimal::new(5, 4) {
                            
                            if let Some(execution) = flash_loan_executor.execute_flash_loan_arbitrage(opportunity) {
                                flash_loan_executor.print_real_execution(&execution);
                                
                                total_executed_profit += execution.net_profit;
                                total_executions += 1;
                                
                                info!("📊 EXECUTION SUMMARY: {} trades | Total profit: ${:.2}", 
                                     total_executions, total_executed_profit);
                                info!("");
                                
                                let _ = exec_stats_tx.send((total_executions, total_executed_profit.to_f64().unwrap_or(0.0)));
                                
                                sleep(Duration::from_millis(100)).await;
                            }
                        }
                    }
                    
                    last_opportunity_count = opportunities.len();
                }
            }
        }
    });
    
    // System monitoring
    loop {
        sleep(Duration::from_secs(15)).await;
        
        let stats = price_engine.get_stats();
        let arb_stats = arbitrage_detector.get_stats();
        let exec_stats = exec_stats_rx.borrow().clone();
        
        info!("📊 LIVE ARBITRAGE TRADING STATUS");
        info!("═══════════════════════════════");
        info!("📡 Live price updates/sec: {:.0}", stats.updates_per_second);
        info!("💾 Active trading pairs: {}", stats.active_pairs);
        info!("🔍 Arbitrage opportunities detected: {}", arb_stats.total_detected);
        info!("⚡ Flash loan trades executed: {}", exec_stats.0);
        if exec_stats.1 > 0.0 {
            info!("💰 Total profit generated: ${:.2}", exec_stats.1);
            info!("📈 Average profit per trade: ${:.2}", exec_stats.1 / exec_stats.0 as f64);
        }
        
        if stats.updates_per_second > 100.0 {
            info!("🚀 HIGH-FREQUENCY MODE: {} price updates/second!", stats.updates_per_second as u64);
        }
        
        if arb_stats.total_detected > 0 {
            info!("💡 ACTIVELY TRADING ARBITRAGE OPPORTUNITIES!");
        }
        
        info!("═══════════════════════════════");
        info!("");
    }
}
