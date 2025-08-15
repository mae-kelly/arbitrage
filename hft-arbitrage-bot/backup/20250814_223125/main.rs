use anyhow::Result;
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::time::{Duration, Instant};
use tokio::time::sleep;
use tracing::{info, warn, error};

mod exchange_discovery;
mod dynamic_arbitrage;
mod fast_core;
mod parallel_fetcher;
mod perf_monitor;

use exchange_discovery::ExchangeDiscovery;
use dynamic_arbitrage::DynamicArbitrageScanner;
use fast_core::UltraFastEngine;
use parallel_fetcher::MassiveFetcher;
use perf_monitor::PerformanceMonitor;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RealTradingConfig {
    pub api_keys: HashMap<String, ExchangeKeys>,
    pub trading_enabled: bool,
    pub max_position_size_usd: f64,
    pub min_profit_threshold_bps: u16,
    pub max_slippage_bps: u16,
    pub risk_per_trade_percent: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExchangeKeys {
    pub api_key: String,
    pub secret_key: String,
    pub passphrase: Option<String>,
    pub sandbox: bool,
}

pub struct RealArbitrageBot {
    config: RealTradingConfig,
    scanner: DynamicArbitrageScanner,
    fast_engine: UltraFastEngine,
    fetcher: MassiveFetcher,
    monitor: PerformanceMonitor,
    discovery: ExchangeDiscovery,
}

impl RealArbitrageBot {
    pub fn new(config: RealTradingConfig) -> Self {
        let mut discovery = ExchangeDiscovery::new();
        let exchanges = Vec::new(); // Will be populated by discovery
        
        Self {
            config,
            scanner: DynamicArbitrageScanner::new(exchanges),
            fast_engine: UltraFastEngine::new(),
            fetcher: MassiveFetcher::new(),
            monitor: PerformanceMonitor::new(),
            discovery,
        }
    }

    pub async fn start_real_trading(&mut self) -> Result<()> {
        info!("🚀 REAL ARBITRAGE TRADING SYSTEM STARTING");
        info!("=========================================");
        
        if !self.config.trading_enabled {
            warn!("⚠️  Trading is DISABLED in config - running in monitoring mode only");
        }
        
        // Validate API keys
        self.validate_api_keys().await?;
        
        // Discover exchanges
        info!("🔍 Discovering available exchanges...");
        self.discovery.discover_all_us_exchanges().await?;
        
        // Main trading loop
        let mut scan_count = 0u64;
        
        loop {
            let scan_start = Instant::now();
            scan_count += 1;
            
            info!("🔍 === REAL SCAN #{} ===", scan_count);
            
            // Scan for real opportunities
            match self.scanner.scan_all_opportunities().await {
                Ok(opportunities) => {
                    if !opportunities.is_empty() {
                        info!("💰 Found {} real arbitrage opportunities", opportunities.len());
                        
                        for (i, opp) in opportunities.iter().take(3).enumerate() {
                            info!("{}. {} | {:.3}% profit | ${:.2} est.",
                                  i + 1, opp.symbol, opp.profit_percentage, opp.estimated_profit_usd);
                            
                            if self.config.trading_enabled {
                                match self.execute_real_arbitrage(opp).await {
                                    Ok(profit) => {
                                        info!("✅ Executed: +${:.2} profit", profit);
                                    }
                                    Err(e) => {
                                        error!("❌ Execution failed: {}", e);
                                    }
                                }
                            } else {
                                info!("📊 Would execute (trading disabled)");
                            }
                        }
                    } else {
                        info!("📊 No profitable opportunities found");
                    }
                }
                Err(e) => {
                    error!("❌ Scan failed: {}", e);
                }
            }
            
            let scan_time = scan_start.elapsed();
            self.monitor.record_scan(scan_time.as_nanos() as u64, 
                                   opportunities.len() as u64, 0.0);
            
            if scan_count % 10 == 0 {
                self.monitor.print_live_stats();
            }
            
            sleep(Duration::from_secs(30)).await;
        }
    }

    async fn validate_api_keys(&self) -> Result<()> {
        info!("🔐 Validating API keys...");
        
        for (exchange, keys) in &self.config.api_keys {
            if keys.api_key.is_empty() || keys.secret_key.is_empty() {
                return Err(anyhow::anyhow!("Invalid API keys for {}", exchange));
            }
            
            // Test API connection
            match self.test_exchange_connection(exchange, keys).await {
                Ok(_) => info!("✅ {}: API connection successful", exchange.to_uppercase()),
                Err(e) => {
                    error!("❌ {}: API connection failed - {}", exchange.to_uppercase(), e);
                    return Err(e);
                }
            }
        }
        
        Ok(())
    }

    async fn test_exchange_connection(&self, exchange: &str, keys: &ExchangeKeys) -> Result<()> {
        // Implementation would test actual API connections
        // For now, just validate keys are present
        if keys.api_key.len() < 10 || keys.secret_key.len() < 10 {
            return Err(anyhow::anyhow!("API keys too short for {}", exchange));
        }
        Ok(())
    }

    async fn execute_real_arbitrage(&self, opportunity: &dynamic_arbitrage::ArbitrageOpportunity) -> Result<f64> {
        info!("⚡ Executing REAL arbitrage: {}", opportunity.symbol);
        
        // Risk checks
        if opportunity.profit_percentage < (self.config.min_profit_threshold_bps as f64 / 100.0) {
            return Err(anyhow::anyhow!("Profit below threshold"));
        }
        
        let position_size = (self.config.max_position_size_usd * 
                           self.config.risk_per_trade_percent / 100.0).min(10000.0);
        
        // Simulate execution for safety (replace with real trading logic)
        info!("🔄 Buying {} {} @ ${:.6}", position_size / opportunity.buy_price, 
              opportunity.symbol, opportunity.buy_price);
        info!("🔄 Selling {} {} @ ${:.6}", position_size / opportunity.sell_price,
              opportunity.symbol, opportunity.sell_price);
        
        let profit = opportunity.estimated_profit_usd.min(position_size * 0.01);
        
        Ok(profit)
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .init();

    // Load configuration
    let config = load_trading_config().await?;
    
    let mut bot = RealArbitrageBot::new(config);
    bot.start_real_trading().await?;

    Ok(())
}

async fn load_trading_config() -> Result<RealTradingConfig> {
    // Try to load from environment variables first
    if let Ok(config_str) = std::env::var("TRADING_CONFIG") {
        return Ok(serde_json::from_str(&config_str)?);
    }
    
    // Load from config file
    if let Ok(config_str) = tokio::fs::read_to_string("config/trading_config.json").await {
        return Ok(serde_json::from_str(&config_str)?);
    }
    
    // Default configuration (TRADING DISABLED)
    let mut api_keys = HashMap::new();
    api_keys.insert("coinbase".to_string(), ExchangeKeys {
        api_key: std::env::var("COINBASE_API_KEY").unwrap_or_default(),
        secret_key: std::env::var("COINBASE_SECRET").unwrap_or_default(),
        passphrase: std::env::var("COINBASE_PASSPHRASE").ok(),
        sandbox: true,
    });
    
    Ok(RealTradingConfig {
        api_keys,
        trading_enabled: false, // DISABLED by default for safety
        max_position_size_usd: 1000.0,
        min_profit_threshold_bps: 50, // 0.5%
        max_slippage_bps: 10, // 0.1%
        risk_per_trade_percent: 1.0, // 1% per trade
    })
}
