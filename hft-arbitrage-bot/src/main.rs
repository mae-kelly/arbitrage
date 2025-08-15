//! Cross-Chain High-Frequency Arbitrage Bot
//! Educational implementation of institutional-grade arbitrage system

use anyhow::Result;
use clap::{Arg, Command};
use std::time::Duration;
use tokio::time::sleep;
use tracing::{info, warn};

mod data_layer;
mod intelligence_layer;
mod execution_layer;
mod settlement_layer;
mod config;
mod monitoring;

use data_layer::DataLayer;
use intelligence_layer::IntelligenceLayer;
use execution_layer::ExecutionLayer;
use settlement_layer::SettlementLayer;

#[derive(Debug)]
pub struct CrossChainArbitrageBot {
    data_layer: DataLayer,
    intelligence_layer: IntelligenceLayer,
    execution_layer: ExecutionLayer,
    settlement_layer: SettlementLayer,
    config: config::BotConfig,
    is_running: bool,
}

impl CrossChainArbitrageBot {
    pub async fn new(config: config::BotConfig) -> Result<Self> {
        let (data_layer, _price_feed_rx) = DataLayer::new();
        
        Ok(Self {
            data_layer,
            intelligence_layer: IntelligenceLayer::new(),
            execution_layer: ExecutionLayer::new(),
            settlement_layer: SettlementLayer::new(),
            config,
            is_running: false,
        })
    }

    pub async fn initialize(&mut self) -> Result<()> {
        info!("🌐 Initializing Cross-Chain HFT Arbitrage System");
        info!("==============================================");
        
        // Initialize all layers
        self.data_layer.initialize_all_feeds().await?;
        self.intelligence_layer.initialize().await?;
        self.execution_layer.initialize().await?;
        self.settlement_layer.initialize().await?;
        
        info!("✅ Cross-chain arbitrage system initialized successfully!");
        info!("");
        info!("🎯 System Capabilities:");
        info!("   • 6+ Blockchain networks (Ethereum, BSC, Arbitrum, Optimism, Polygon, Solana)");
        info!("   • 10+ Major exchanges (Binance, Coinbase, Uniswap, PancakeSwap, etc.)");
        info!("   • Flash loan integration (Aave, dYdX, Balancer)");
        info!("   • Cross-chain bridging (LayerZero, Stargate, Axelar)");
        info!("   • MEV protection and gas optimization");
        info!("   • ML-powered opportunity detection");
        info!("   • Risk management and compliance reporting");
        info!("");
        
        Ok(())
    }

    pub async fn start_trading(&mut self) -> Result<()> {
        info!("🚀 Starting cross-chain arbitrage trading...");
        info!("⚠️  SIMULATION MODE - No real trades executed");
        info!("");
        
        self.is_running = true;
        let mut cycle_count = 0u64;
        
        // Start background monitoring
        let monitoring_handle = tokio::spawn(async {
            monitoring::start_prometheus_server().await;
        });

        while self.is_running {
            cycle_count += 1;
            let cycle_start = std::time::Instant::now();
            
            info!("🔄 === ARBITRAGE CYCLE #{} ===", cycle_count);
            
            // 1. Get latest market data from all chains and exchanges
            let market_data = self.data_layer.get_latest_market_data().await?;
            info!("📊 Processed {} market data points", market_data.len());
            
            // 2. Analyze for arbitrage opportunities using AI
            let strategies = self.intelligence_layer.analyze_opportunities(&market_data).await?;
            info!("🧠 Found {} profitable strategies", strategies.len());
            
            if !strategies.is_empty() {
                info!("");
                info!("💰 🚀 CROSS-CHAIN ARBITRAGE OPPORTUNITIES 🚀");
                info!("============================================");
                
                for (i, strategy) in strategies.iter().take(5).enumerate() {
                    info!("{}. {} | Profit: ${:.2} | Confidence: {:.1}%", 
                          i + 1, 
                          strategy.opportunity.symbol,
                          strategy.expected_profit_usd,
                          strategy.ml_confidence * 100.0);
                    
                    if strategy.opportunity.cross_chain_involved {
                        info!("   🌉 Cross-chain: {} → {}", 
                              get_chain_name(strategy.opportunity.buy_chain.unwrap_or(1)),
                              get_chain_name(strategy.opportunity.sell_chain.unwrap_or(1)));
                    }
                    
                    if strategy.flash_loan_strategy.is_some() {
                        info!("   ⚡ Flash loan: ${:.0} at {:.3}% fee", 
                              strategy.flash_loan_strategy.as_ref().unwrap().amount,
                              strategy.flash_loan_strategy.as_ref().unwrap().fee_rate * 100.0);
                    }
                    
                    if strategy.bridge_strategy.is_some() {
                        info!("   🌉 Bridge time: {} minutes", 
                              strategy.bridge_strategy.as_ref().unwrap().estimated_time_minutes);
                    }
                    
                    info!("   📊 Expected execution: {}ms | Gas: ${:.2}", 
                          strategy.execution_plan.total_estimated_time_ms,
                          strategy.gas_optimization.gas_limit_buffer * 50.0); // Estimate
                }
                info!("");
                
                // 3. Execute top strategies
                for strategy in strategies.into_iter().take(3) {
                    match self.execution_layer.execute_strategy(strategy.clone()).await {
                        Ok(result) => {
                            info!("✅ Executed {}: ${:.2} profit in {}ms", 
                                  strategy.strategy_id, result.total_profit_usd, result.execution_time_ms);
                            
                            // 4. Record results for learning
                            self.settlement_layer.record_execution_result(result).await?;
                        }
                        Err(e) => {
                            warn!("❌ Failed to execute {}: {}", strategy.strategy_id, e);
                        }
                    }
                }
            } else {
                info!("📊 No profitable arbitrage opportunities found this cycle");
            }
            
            let cycle_time = cycle_start.elapsed();
            info!("⏱️  Cycle {} completed in {}ms", cycle_count, cycle_time.as_millis());
            
            // Performance summary every 10 cycles
            if cycle_count % 10 == 0 {
                let performance = self.settlement_layer.get_performance_summary().await?;
                info!("");
                info!("📈 PERFORMANCE SUMMARY (Last 10 cycles):");
                info!("=========================================");
                info!("💰 Total simulated profit: ${:.2}", performance.total_profit);
                info!("🎯 Successful executions: {}/{}", performance.successful_trades, performance.total_trades);
                info!("⚡ Average execution time: {}ms", performance.avg_execution_time_ms);
                info!("🌉 Cross-chain trades: {}", performance.cross_chain_trades);
                info!("⚡ Flash loan utilization: {:.1}%", performance.flash_loan_usage_pct);
                info!("");
            }
            
            // Wait before next cycle
            info!("⏰ Next cycle in {} seconds...", self.config.scan_interval_seconds);
            info!("════════════════════════════════════════════");
            info!("");
            
            sleep(Duration::from_secs(self.config.scan_interval_seconds)).await;
        }
        
        // Cleanup
        monitoring_handle.abort();
        Ok(())
    }

    pub async fn shutdown(&mut self) -> Result<()> {
        info!("🛑 Shutting down cross-chain arbitrage system...");
        self.is_running = false;
        
        // Generate final report
        let final_performance = self.settlement_layer.get_performance_summary().await?;
        
        info!("");
        info!("📊 FINAL PERFORMANCE REPORT:");
        info!("============================");
        info!("💰 Total simulated profit: ${:.2}", final_performance.total_profit);
        info!("📈 Total trades executed: {}", final_performance.total_trades);
        info!("🎯 Success rate: {:.1}%", final_performance.success_rate * 100.0);
        info!("⚡ Flash loan trades: {}", final_performance.flash_loan_trades);
        info!("🌉 Cross-chain trades: {}", final_performance.cross_chain_trades);
        info!("");
        info!("✅ System shutdown complete");
        
        Ok(())
    }
}

fn get_chain_name(chain_id: u64) -> &'static str {
    match chain_id {
        1 => "Ethereum",
        56 => "BSC",
        137 => "Polygon", 
        42161 => "Arbitrum",
        10 => "Optimism",
        1399811149 => "Solana",
        _ => "Unknown",
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .with_target(false)
        .init();

    // Parse command line arguments
    let matches = Command::new("Cross-Chain HFT Arbitrage Bot")
        .version("5.0.0")
        .about("Educational cross-chain arbitrage system")
        .arg(Arg::new("config")
            .short('c')
            .long("config")
            .value_name("FILE")
            .help("Configuration file path")
            .default_value("config/default.toml"))
        .arg(Arg::new("mode")
            .short('m')
            .long("mode")
            .value_name("MODE")
            .help("Trading mode")
            .value_parser(["simulation", "testnet", "mainnet"])
            .default_value("simulation"))
        .get_matches();

    let config_path = matches.get_one::<String>("config").unwrap();
    let mode = matches.get_one::<String>("mode").unwrap();

    println!("🌐 CROSS-CHAIN HFT ARBITRAGE SYSTEM v5.0");
    println!("=========================================");
    println!("⚠️  Educational implementation only");
    println!("⚠️  Real trading requires proper licenses");
    println!("📊 Mode: {}", mode.to_uppercase());
    println!("⚙️  Config: {}", config_path);
    println!("");

    // Load configuration
    let config = config::BotConfig::load(config_path)?;
    
    // Create and initialize the bot
    let mut bot = CrossChainArbitrageBot::new(config).await?;
    bot.initialize().await?;
    
    // Setup graceful shutdown
    let (shutdown_tx, mut shutdown_rx) = tokio::sync::oneshot::channel();
    
    tokio::spawn(async move {
        tokio::signal::ctrl_c().await.expect("Failed to listen for Ctrl+C");
        let _ = shutdown_tx.send(());
    });
    
    // Start trading in a separate task
    let bot_handle = tokio::spawn(async move {
        bot.start_trading().await
    });
    
    // Wait for shutdown signal or bot completion
    tokio::select! {
        _ = shutdown_rx => {
            info!("📡 Shutdown signal received");
        }
        result = bot_handle => {
            match result {
                Ok(Ok(())) => info!("🎯 Bot completed successfully"),
                Ok(Err(e)) => warn!("❌ Bot error: {}", e),
                Err(e) => warn!("❌ Bot task error: {}", e),
            }
        }
    }
    
    info!("👋 Cross-chain arbitrage system stopped");
    Ok(())
}
