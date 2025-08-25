use ethers::prelude::*;
use std::sync::Arc;
use tokio::sync::RwLock;
use dashmap::DashMap;
use std::env;

mod arbitrage;
mod flashloan;
mod mempool;
mod ml_predictor;
mod executor;

use arbitrage::{ArbitrageEngine, Opportunity};
use flashloan::FlashLoanManager;
use mempool::MempoolMonitor;
use ml_predictor::MLPredictor;
use executor::TradeExecutor;

#[derive(Clone)]
pub struct Config {
    pub mode: String,
    pub alchemy_key: String,
    pub infura_key: String,
    pub etherscan_key: String,
    pub wallet_address: String,
    pub private_key: String,
    pub network: String,
    pub rpc_url: String,
    pub strategies: String,
    pub min_profit_usd: f64,
    pub max_gas_gwei: u64,
    pub use_aave: bool,
    pub use_balancer: bool,
    pub use_uniswap: bool,
    pub flashbots_enabled: bool,
    pub private_mempool: bool,
}

impl Config {
    fn load() -> Self {
        dotenv::dotenv().ok();
        Self {
            mode: env::var("MODE").unwrap_or_else(|_| "test".to_string()),
            alchemy_key: env::var("ALCHEMY_KEY").unwrap_or_default(),
            infura_key: env::var("INFURA_KEY").unwrap_or_default(),
            etherscan_key: env::var("ETHERSCAN_KEY").unwrap_or_default(),
            wallet_address: env::var("WALLET_ADDRESS").unwrap_or_default(),
            private_key: env::var("PRIVATE_KEY").unwrap_or_default(),
            network: env::var("NETWORK").unwrap_or_else(|_| "fork".to_string()),
            rpc_url: env::var("RPC_URL").unwrap_or_else(|_| "http://127.0.0.1:8545".to_string()),
            strategies: env::var("STRATEGIES").unwrap_or_else(|_| "all".to_string()),
            min_profit_usd: env::var("MIN_PROFIT_USD").unwrap_or_else(|_| "100".to_string()).parse().unwrap_or(100.0),
            max_gas_gwei: env::var("MAX_GAS_GWEI").unwrap_or_else(|_| "50".to_string()).parse().unwrap_or(50),
            use_aave: env::var("USE_AAVE").unwrap_or_else(|_| "true".to_string()).parse().unwrap_or(true),
            use_balancer: env::var("USE_BALANCER").unwrap_or_else(|_| "true".to_string()).parse().unwrap_or(true),
            use_uniswap: env::var("USE_UNISWAP").unwrap_or_else(|_| "true".to_string()).parse().unwrap_or(true),
            flashbots_enabled: env::var("FLASHBOTS_ENABLED").unwrap_or_else(|_| "false".to_string()).parse().unwrap_or(false),
            private_mempool: env::var("PRIVATE_MEMPOOL").unwrap_or_else(|_| "false".to_string()).parse().unwrap_or(false),
        }
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    env_logger::init();
    let config = Arc::new(Config::load());
    
    let provider = Provider::<Http>::try_from(&config.rpc_url)?;
    let wallet = config.private_key.parse::<LocalWallet>()?;
    let client = Arc::new(SignerMiddleware::new(provider, wallet));
    
    let ml_predictor = Arc::new(MLPredictor::new());
    let flashloan_manager = Arc::new(FlashLoanManager::new(client.clone(), config.clone()));
    let mempool_monitor = Arc::new(MempoolMonitor::new(Arc::new(client.provider().clone())));
    let arbitrage_engine = Arc::new(ArbitrageEngine::new(client.clone(), ml_predictor.clone()));
    let _executor = Arc::new(TradeExecutor::new(client.clone(), config.clone()));
    
    let opportunities: Arc<DashMap<String, Opportunity>> = Arc::new(DashMap::new());
    let _active_trades = Arc::new(RwLock::new(Vec::<arbitrage::Opportunity>::new()));
    
    let mempool_handle = tokio::spawn({
        let mempool_monitor = mempool_monitor.clone();
        let opportunities = opportunities.clone();
        async move {
            mempool_monitor.start_monitoring(opportunities).await
        }
    });
    
    let arbitrage_handle = tokio::spawn({
        let arbitrage_engine = arbitrage_engine.clone();
        let opportunities = opportunities.clone();
        let flashloan_manager = flashloan_manager.clone();
        async move {
            loop {
                // Iterate over the DashMap entries directly
                for entry in opportunities.iter() {
                    let key = entry.key().clone();
                    let opp_ref = opportunities.get(&key);
                    if let Some(opp_ref) = opp_ref {
                        if let Ok(profit) = arbitrage_engine.calculate_profit(&opp_ref).await {
                            if profit > 0.0 {
                                let _ = flashloan_manager.execute_arbitrage(opp_ref).await;
                            }
                        }
                    }
                }
                tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
            }
        }
    });
    
    let ml_handle = tokio::spawn({
        let ml_predictor = ml_predictor.clone();
        let opportunities = opportunities.clone();
        async move {
            loop {
                let data: Vec<_> = opportunities.iter().map(|x| x.value().clone()).collect();
                if !data.is_empty() {
                    ml_predictor.update_predictions(data).await;
                }
                tokio::time::sleep(tokio::time::Duration::from_secs(1)).await;
            }
        }
    });
    
    tokio::select! {
        _ = mempool_handle => {},
        _ = arbitrage_handle => {},
        _ = ml_handle => {},
        _ = tokio::signal::ctrl_c() => {
            println!("Shutting down...");
        }
    }
    
    Ok(())
}
