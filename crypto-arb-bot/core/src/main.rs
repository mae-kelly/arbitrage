mod exchanges;
mod bridges;
mod execution;
mod risk;
mod monitoring;

use anyhow::Result;
use std::sync::Arc;
use tokio::time::{interval, Duration};

#[tokio::main]
async fn main() -> Result<()> {
    let binance = exchanges::binance::BinanceConnector::new(
        std::env::var("BINANCE_API_KEY")?,
        std::env::var("BINANCE_SECRET")?
    );
    
    let uniswap = exchanges::uniswap::UniswapConnector::new("https://eth-mainnet.g.alchemy.com/v2/demo").await?;
    
    let executor = execution::production::ProductionExecutor::new(
        &std::env::var("PRIVATE_KEY")?,
        vec!["https://eth-mainnet.g.alchemy.com/v2/demo"]
    ).await?;
    
    let risk_manager = Arc::new(risk::manager::RiskManager::new(100000.0, 5000.0));
    
    let alert_manager = monitoring::alerts::AlertManager::new(
        std::env::var("SLACK_WEBHOOK_URL")?
    );

    let mut scan_interval = interval(Duration::from_millis(500));
    
    loop {
        scan_interval.tick().await;
        
        if risk_manager.emergency_stop().await {
            alert_manager.send_error_alert("Emergency stop triggered").await?;
            break;
        }
        
        let binance_price = binance.get_price("BTCUSDT").await?;
        let usdc: ethers::types::Address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48".parse()?;
        let weth: ethers::types::Address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2".parse()?;
        let amount = ethers::types::U256::from(1000) * ethers::types::U256::exp10(6);
        
        let uniswap_quote = uniswap.get_quote(usdc, weth, amount).await?;
        let uniswap_price = uniswap_quote.as_u128() as f64 / 1e18;
        
        let spread = (binance_price - uniswap_price).abs() / binance_price;
        
        if spread > 0.005 && risk_manager.can_execute_trade("BTC", 10000.0).await {
            let profit = spread * 10000.0 - 50.0;
            
            if profit > 100.0 {
                println!("Executing arbitrage: Binance ${:.2} vs Uniswap ${:.2}", binance_price, uniswap_price);
                
                let tx_hash = executor.execute_flash_arbitrage(usdc, amount, usdc, weth).await?;
                println!("Transaction: {:?}", tx_hash);
                
                risk_manager.record_trade("BTC", 10000.0, profit).await;
                alert_manager.send_profit_alert(profit, "BTC CEX-DEX").await?;
            }
        }
    }
    
    Ok(())
}
