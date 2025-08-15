//! Cross-chain bridge integrations

use ethers::prelude::*;
use anyhow::Result;
use serde::{Serialize, Deserialize};

pub mod layerzero;
pub mod stargate;
pub mod axelar;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BridgeTransaction {
    pub from_chain: u64,
    pub to_chain: u64,
    pub token: Address,
    pub amount: U256,
    pub recipient: Address,
    pub estimated_time_minutes: u32,
    pub estimated_fee: U256,
}

pub trait Bridge {
    async fn estimate_fee(&self, tx: &BridgeTransaction) -> Result<U256>;
    async fn execute_bridge(&self, tx: &BridgeTransaction) -> Result<H256>;
    async fn get_transaction_status(&self, tx_hash: H256) -> Result<BridgeStatus>;
}

#[derive(Debug, Clone)]
pub enum BridgeStatus {
    Pending,
    InProgress,
    Completed,
    Failed(String),
}

pub struct BridgeRouter {
    layerzero: layerzero::LayerZeroClient,
    stargate: stargate::StargateClient,
    axelar: axelar::AxelarClient,
}

impl BridgeRouter {
    pub fn new() -> Self {
        Self {
            layerzero: layerzero::LayerZeroClient::new(),
            stargate: stargate::StargateClient::new(),
            axelar: axelar::AxelarClient::new(),
        }
    }
    
    pub async fn find_optimal_route(&self, tx: &BridgeTransaction) -> Result<String> {
        let lz_fee = self.layerzero.estimate_fee(tx).await?;
        let sg_fee = self.stargate.estimate_fee(tx).await?;
        let ax_fee = self.axelar.estimate_fee(tx).await?;
        
        if lz_fee <= sg_fee && lz_fee <= ax_fee {
            Ok("layerzero".to_string())
        } else if sg_fee <= ax_fee {
            Ok("stargate".to_string())
        } else {
            Ok("axelar".to_string())
        }
    }
}
