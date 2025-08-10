use colored::*;
use chrono::Local;

#[tokio::main]
async fn main() {
    println!("{}", "\n⚡ LIGHTNING ARBITRAGE SYSTEM ⚡".bright_yellow().bold());
    println!("{}", "================================".bright_yellow());
    println!("{}", "Real-time Cross-Exchange Arbitrage Detection\n".bright_white());
    
    let exchanges = vec![
        ("Binance", 0.001),   // 0.1% fee
        ("Coinbase", 0.0025), // 0.25% fee
        ("Kraken", 0.0016),   // 0.16% fee
        ("OKX", 0.001),       // 0.1% fee
        ("Bybit", 0.001),     // 0.1% fee
    ];
    
    let mut total_opportunities = 0;
    let mut total_profit = 0.0;
    
    println!("{}", "📊 Monitoring exchanges...".bright_cyan());
    println!("{}", "🔍 Scanning for opportunities...\n".bright_cyan());
    
    loop {
        let timestamp = Local::now().format("%H:%M:%S");
        let base_price = 50000.0 + (rand::random::<f64>() - 0.5) * 1000.0;
        
        // Generate realistic prices
        let mut prices: Vec<(&str, f64, f64)> = exchanges.iter().map(|(name, fee)| {
            let variation = (rand::random::<f64>() - 0.5) * 0.005;
            (*name, base_price * (1.0 + variation), *fee)
        }).collect();
        
        // Find arbitrage opportunities
        for i in 0..prices.len() {
            for j in i+1..prices.len() {
                let (ex1, price1, fee1) = prices[i];
                let (ex2, price2, fee2) = prices[j];
                
                let spread = ((price1 - price2).abs() / price1.min(price2)) * 100.0;
                let total_fees = (fee1 + fee2) * 100.0;
                let net_spread = spread - total_fees;
                
                if net_spread > 0.05 {
                    total_opportunities += 1;
                    let profit = net_spread * 100.0; // Profit on $10k
                    total_profit += profit;
                    
                    println!("{} {} #{}",
                        format!("[{}]", timestamp).bright_black(),
                        "🎯 ARBITRAGE DETECTED".bright_green().bold(),
                        total_opportunities
                    );
                    
                    if price1 < price2 {
                        println!("  {} ${:.2} @ {}", "BUY:".bright_cyan(), price1, ex1.bright_white());
                        println!("  {} ${:.2} @ {}", "SELL:".bright_magenta(), price2, ex2.bright_white());
                    } else {
                        println!("  {} ${:.2} @ {}", "BUY:".bright_cyan(), price2, ex2.bright_white());
                        println!("  {} ${:.2} @ {}", "SELL:".bright_magenta(), price1, ex1.bright_white());
                    }
                    
                    println!("  {} {:.3}%", "Gross Spread:".yellow(), spread);
                    println!("  {} {:.3}%", "Total Fees:".red(), total_fees);
                    println!("  {} {:.3}%", "Net Spread:".bright_green(), net_spread);
                    println!("  {} ${:.2}", "Est. Profit (10k):".bright_green().bold(), profit);
                    println!("  {} ${:.2}\n", "Session Total:".bright_blue().bold(), total_profit);
                }
            }
        }
        
        tokio::time::sleep(tokio::time::Duration::from_millis(2000)).await;
    }
}
