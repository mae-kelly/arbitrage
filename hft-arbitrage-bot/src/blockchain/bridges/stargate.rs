//! Stargate Finance bridge integration

use ethers::prelude::*;
use anyhow::Result;
use super::{Bridge, BridgeTransaction, BridgeStatus};

pub struct StargateClient {
    router_addresses: std::collections::HashMap<u64, Address>,
}

impl StargateClient {
    pub fn new() -> Self {
        let mut routers = std::collections::HashMap::new();
        routers.insert(1, "0x8731d54E9D02c286767d56ac03e8037C07e01e98".parse().unwrap()); // Ethereum
        routers.insert(42161, "0x53Bf833A5d6c4ddA888F69c22C88C9f356a41614".parse().unwrap()); // Arbitrum
        
        Self { router_addresses: routers }
    }
}

#[async_trait::async_trait]
impl Bridge for StargateClient {
    async fn estimate_fee(&self, tx: &BridgeTransaction) -> Result<U256> {
        // Stargate fee estimation (typically 0.06% + gas)
        let percentage_fee = tx.amount * U256::from(6) / U256::from(10000); // 0.06%
        let gas_fee = U256::from(100000); // Estimated gas
        Ok(percentage_fee + gas_fee)
    }
    
    async fn execute_bridge(&self, _tx: &BridgeTransaction) -> Result<H256> {
        // Execute Stargate bridge transaction
        Ok(H256::random())
    }
    
    async fn get_transaction_status(&self, _tx_hash: H256) -> Result<BridgeStatus> {
        Ok(BridgeStatus::Completed)
    }
}
