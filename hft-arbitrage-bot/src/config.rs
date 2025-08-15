//! Configuration management for cross-chain arbitrage bot

use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BotConfig {
    pub scan_interval_seconds: u64,
    pub chains: HashMap<String, ChainConfig>,
    pub exchanges: HashMap<String, ExchangeConfig>,
    pub risk_limits: RiskLimits,
    pub flash_loans: FlashLoanConfig,
    pub bridges: BridgeConfig,
    pub mev_protection: MEVConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChainConfig {
    pub chain_id: u64,
    pub rpc_url: String,
    pub gas_limit: u64,
    pub max_gas_price_gwei: f64,
    pub confirmation_blocks: u64,
    pub enabled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExchangeConfig {
    pub api_key: Option<String>,
    pub secret: Option<String>,
    pub base_url: String,
    pub rate_limit_ms: u64,
    pub enabled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskLimits {
    pub max_position_usd: f64,
    pub max_daily_volume_usd: f64,
    pub max_slippage_pct: f64,
    pub max_gas_price_gwei: f64,
    pub min_profit_usd: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlashLoanConfig {
    pub enabled: bool,
    pub max_loan_usd: f64,
    pub providers: Vec<String>,
    pub gas_buffer_pct: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BridgeConfig {
    pub enabled: bool,
    pub max_bridge_amount_usd: f64,
    pub providers: Vec<String>,
    pub max_wait_time_minutes: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MEVConfig {
    pub use_private_mempool: bool,
    pub flashbots_enabled: bool,
    pub gas_price_boost_pct: f64,
}

impl BotConfig {
    pub fn load(path: &str) -> Result<Self> {
        // For simulation, return default config
        Ok(Self::default())
    }
}

impl Default for BotConfig {
    fn default() -> Self {
        let mut chains = HashMap::new();
        chains.insert("ethereum".to_string(), ChainConfig {
            chain_id: 1,
            rpc_url: "wss://eth-mainnet.g.alchemy.com/v2/demo".to_string(),
            gas_limit: 500000,
            max_gas_price_gwei: 100.0,
            confirmation_blocks: 2,
            enabled: true,
        });
        
        chains.insert("bsc".to_string(), ChainConfig {
            chain_id: 56,
            rpc_url: "wss://bsc-dataseed1.binance.org".to_string(),
            gas_limit: 300000,
            max_gas_price_gwei: 20.0,
            confirmation_blocks: 3,
            enabled: true,
        });

        let mut exchanges = HashMap::new();
        exchanges.insert("binance".to_string(), ExchangeConfig {
            api_key: None,
            secret: None,
            base_url: "https://api.binance.com".to_string(),
            rate_limit_ms: 100,
            enabled: true,
        });

        Self {
            scan_interval_seconds: 10,
            chains,
            exchanges,
            risk_limits: RiskLimits {
                max_position_usd: 100000.0,
                max_daily_volume_usd: 1000000.0,
                max_slippage_pct: 2.0,
                max_gas_price_gwei: 100.0,
                min_profit_usd: 50.0,
            },
            flash_loans: FlashLoanConfig {
                enabled: true,
                max_loan_usd: 500000.0,
                providers: vec!["aave".to_string(), "dydx".to_string()],
                gas_buffer_pct: 20.0,
            },
            bridges: BridgeConfig {
                enabled: true,
                max_bridge_amount_usd: 100000.0,
                providers: vec!["layerzero".to_string(), "stargate".to_string()],
                max_wait_time_minutes: 30,
            },
            mev_protection: MEVConfig {
                use_private_mempool: true,
                flashbots_enabled: true,
                gas_price_boost_pct: 10.0,
            },
        }
    }
}
