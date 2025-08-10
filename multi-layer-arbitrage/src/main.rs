mod websocket_feeds;
mod strategy_engine;
mod execution_engine;

use websocket_feeds::WebSocketManager;
use strategy_engine::StrategyEngine;
use execution_engine::ExecutionEngine;
use colored::*;
use tokio::time::{sleep, Duration, interval};
use std::sync::Arc;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    print_banner();
    
    let (ws_manager, mut price_receiver) = WebSocketManager::new();
    let strategy_engine = Arc::new(StrategyEngine::new());
    let execution_engine = Arc::new(ExecutionEngine::new());
    
    println!("{}", "🚀 Initializing Multi-Layer Arbitrage System...".green().bold());
    println!("{}", "📡 Connecting to WebSocket feeds...".cyan());
    
    ws_manager.connect_all_feeds().await;
    
    sleep(Duration::from_secs(2)).await;
    
    println!("{}", "✅ All feeds connected!".green().bold());
    println!("{}", "🔍 Scanning for arbitrage opportunities...".yellow());
    println!();
    
    // Background task to show we're receiving prices
    let prices_for_display = ws_manager.prices.clone();
    tokio::spawn(async move {
        while let Ok(update) = price_receiver.recv().await {
            println!("📊 Price Update: {} @ ${:.2} (bid: ${:.2}, ask: ${:.2})",
                update.exchange.cyan(),
                (update.bid + update.ask) / 2.0,
                update.bid,
                update.ask
            );
        }
    });
    
    let mut scan_interval = interval(Duration::from_millis(500)); // Check every 500ms
    let mut counter = 0u64;
    let mut total_opportunities = 0u64;
    
    loop {
        scan_interval.tick().await;
        counter += 1;
        
        // Show current prices every 2 seconds
        if counter % 4 == 0 {
            println!("\n{}", "📈 Current Prices:".blue().bold());
            for entry in ws_manager.prices.iter() {
                let price = entry.value();
                println!("  {} - Bid: ${:.2} | Ask: ${:.2} | Spread: ${:.2}",
                    price.exchange.yellow(),
                    price.bid,
                    price.ask,
                    price.ask - price.bid
                );
            }
        }
        
        let opportunities = strategy_engine.analyze_prices(&ws_manager.prices);
        
        if !opportunities.is_empty() {
            total_opportunities += opportunities.len() as u64;
            println!("\n{} {} OPPORTUNITIES DETECTED! Total found: {}",
                "🎯".red().bold(),
                opportunities.len(),
                total_opportunities
            );
            
            for (i, opp) in opportunities.iter().take(5).enumerate() {
                println!("  {}. {} → {} | Buy: ${:.2} | Sell: ${:.2} | Profit: {:.3}% (${:.2})",
                    i + 1,
                    opp.buy_exchange.blue(),
                    opp.sell_exchange.green(),
                    opp.buy_price,
                    opp.sell_price,
                    opp.profit_percentage,
                    opp.estimated_profit_usd
                );
                
                // Execute if profitable enough
                if opp.profit_percentage > rust_decimal_macros::dec!(0.05) {
                    let exec = execution_engine.clone();
                    let opp = opp.clone();
                    tokio::spawn(async move {
                        let _ = exec.execute_opportunity(&opp).await;
                    });
                }
            }
        }
        
        // Status update every 10 seconds
        if counter % 20 == 0 {
            println!("\n{}", "📊 Status Report:".magenta().bold());
            println!("  Scans completed: {}", counter);
            println!("  Total opportunities found: {}", total_opportunities);
            println!("  Active price feeds: {}", ws_manager.prices.len());
            println!("  Scan rate: {} scans/second", 2);
        }
    }
}

fn print_banner() {
    println!("\n{}", "╔══════════════════════════════════════════════════════════════╗".cyan().bold());
    println!("{}", "║         MULTI-LAYER ARBITRAGE SYSTEM v2.0                   ║".cyan().bold());
    println!("{}", "║         Real-Time L1 + L2 Opportunity Scanner               ║".cyan().bold());
    println!("{}", "╚══════════════════════════════════════════════════════════════╝".cyan().bold());
    println!();
}
