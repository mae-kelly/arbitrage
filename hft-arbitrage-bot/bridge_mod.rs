use crate::blockchain::types::{Address, U256, H256, Result};
use serde::{Deserialize, Serialize};

pub mod layerzero;
pub mod stargate;
pub mod axelar;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BridgeTransaction {
    pub from_chain_id: u64,
    pub to_chain_id: u64,
    pub token: Address,
    pub amount: U256,
    pub recipient: Address,
    pub deadline: u64,
    pub estimated_fee: U256,
}

#[async_trait::async_trait]
pub trait Bridge: Send + Sync {
    async fn estimate_fee(&self, tx: &BridgeTransaction) -> Result<U256>;
    async fn execute_bridge(&self, tx: &BridgeTransaction) -> Result<H256>;
    async fn get_transaction_status(&self, tx_hash: H256) -> Result<BridgeStatus>;
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum BridgeStatus {
    Pending,
    Confirmed,
    Failed,
    Unknown,
}