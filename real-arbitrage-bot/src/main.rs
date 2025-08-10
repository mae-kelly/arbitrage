use colored::*;
use chrono::Local;
use serde::Deserialize;
use std::collections::HashMap;
use anyhow::Result;

#[derive(Deserialize, Debug)]
struct BinancePrice {
    symbol: String,
    price: String,
}

async fn get_binance_price() -> Result<f64> {
    let url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT";
    let response = reqwest::get(url).await?;
    let price_data: BinancePrice = response.json().await?;
    Ok(price_data.price.parse()?)
}

async fn get_coinbase_price() -> Result<f64> {
    let url = "https://api.coinbase.com/v2/exchange-rates?currency=BTC";
    let response = reqwest::get(url).await?;
    let data: serde_json::Value = response.json().await?;
    
    if let Some(usd_rate) = data["data"]["rates"]["USD"].as_str() {
        Ok(usd_rate.parse()?)
    } else {
        Err(anyhow::anyhow!("Failed to parse Coinbase price"))
    }
}

async fn get_kraken_price() -> Result<f64> {
    let url = "https://api.kraken.com/0/public/Ticker?pair=XBTUSD";
    let response = reqwest::get(url).await?;
    let text = response.text().await?;
    
    // Parse Kraken's response
    let data: serde_json::Value = serde_json::from_str(&text)?;
    if let Some(ticker) = data["result"]["XXBTZUSD"]["a"][0].as_str() {
        Ok(ticker.parse()?)
    } else {
        Err(anyhow::anyhow!("Failed to parse Kraken price"))
    }
}

#[tokio::main]
async fn main() {
    println!("{}", "\n📡 REAL BITCOIN PRICE MONITOR".bright_yellow().bold());
    println!("{}", "==============================".bright_yellow());
    println!("{}", "Fetching LIVE prices from exchanges...\n".bright_cyan());
    
    let mut total_opportunities = 0;
    let mut session_profit = 0.0;
    
    // Real exchange fees
    let fees = HashMap::from([
        ("Binance", 0.001),   // 0.1%
        ("Coinbase", 0.005),  // 0.5%
        ("Kraken", 0.0026),   // 0.26%
    ]);
    
    loop {
        let timestamp = Local::now().format("%H:%M:%S");
        let mut prices = Vec::new();
        
        // Fetch REAL prices
        print!("Fetching prices");
        
        match get_binance_price().await {
            Ok(price) => {
                prices.push(("Binance", price, *fees.get("Binance").unwrap()));
                print!(".");
            }
            Err(_) => print!("x"),
        }
        
        match get_coinbase_price().await {
            Ok(price) => {
                prices.push(("Coinbase", price, *fees.get("Coinbase").unwrap()));
                print!(".");
            }
            Err(_) => print!("x"),
        }
        
        match get_kraken_price().await {
            Ok(price) => {
                prices.push(("Kraken", price, *fees.get("Kraken").unwrap()));
                println!(" ✓");
            }
            Err(_) => println!(" x"),
        }
        
        // Display current REAL prices
        if !prices.is_empty() {
            println!("\n{} {}", 
                format!("[{}]", timestamp).bright_black(),
                "LIVE Bitcoin Prices:".bright_white().bold()
            );
            
            let mut min_price = f64::MAX;
            let mut max_price = f64::MIN;
            let mut min_exchange = "";
            let mut max_exchange = "";
            
            for (exchange, price, _) in &prices {
                println!("  {} ${:.2}", 
                    format!("{:10}", exchange).bright_cyan(),
                    price
                );
                
                if *price < min_price {
                    min_price = *price;
                    min_exchange = exchange;
                }
                if *price > max_price {
                    max_price = *price;
                    max_exchange = exchange;
                }
            }
            
            // Calculate REAL spread
            let spread_dollars = max_price - min_price;
            let spread_percent = (spread_dollars / min_price) * 100.0;
            
            println!("\n  {} ${:.2} ({})", 
                "Lowest:".green(), min_price, min_exchange
            );
            println!("  {} ${:.2} ({})", 
                "Highest:".red(), max_price, max_exchange
            );
            println!("  {} ${:.2} ({:.4}%)", 
                "Spread:".yellow(), spread_dollars, spread_percent
            );
            
            // Check for REAL arbitrage
            let buy_fee = fees.get(min_exchange).unwrap_or(&0.001);
            let sell_fee = fees.get(max_exchange).unwrap_or(&0.001);
            let total_fees = (buy_fee + sell_fee) * 100.0;
            let net_spread = spread_percent - total_fees;
            
            if net_spread > 0.0 {
                total_opportunities += 1;
                let profit_on_10k = net_spread * 100.0;
                session_profit += profit_on_10k;
                
                println!("\n{} {}", 
                    "🎯 REAL ARBITRAGE DETECTED!".bright_green().bold(),
                    format!("#{}", total_opportunities).bright_yellow()
                );
                println!("  {} ${:.2} @ {}", "BUY:".bright_cyan(), min_price, min_exchange);
                println!("  {} ${:.2} @ {}", "SELL:".bright_magenta(), max_price, max_exchange);
                println!("  {} {:.4}%", "Gross Spread:".yellow(), spread_percent);
                println!("  {} {:.4}%", "Total Fees:".red(), total_fees);
                println!("  {} {:.4}%", "NET PROFIT:".bright_green().bold(), net_spread);
                println!("  {} ${:.2}", "On $10k trade:".green(), profit_on_10k);
                println!("  {} ${:.2}", "Session Total:".bright_blue(), session_profit);
            } else {
                println!("  {} Spread too small after fees", "❌".red());
            }
        }
        
        println!("\nWaiting 15 seconds...\n");
        tokio::time::sleep(tokio::time::Duration::from_secs(15)).await;
    }
}
