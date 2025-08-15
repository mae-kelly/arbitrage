//! Arbitrum L2 integration

use ethers::prelude::*;
use anyhow::Result;

pub struct ArbitrumClient {
    provider: Provider<Ws>,
    chain_id: u64,
    sequencer_url: String,
}

impl ArbitrumClient {
    pub async fn new() -> Result<Self> {
        let provider = Provider::<Ws>::connect("wss://arb1.arbitrum.io/ws").await?;
        let chain_id = 42161;
        
        Ok(Self {
            provider,
            chain_id,
            sequencer_url: "https://arb1.arbitrum.io/rpc".to_string(),
        })
    }
    
    pub async fn get_l1_gas_price(&self) -> Result<U256> {
        // Get L1 gas price for Arbitrum fee calculation
        let l1_gas_price = self.provider
            .request::<(), U256>("eth_gasPrice", ())
            .await?;
        Ok(l1_gas_price)
    }
    
    pub async fn estimate_total_fee(&self, tx: &TypedTransaction) -> Result<U256> {
        let l2_gas = self.provider.estimate_gas(tx).await?;
        let l2_gas_price = self.provider.get_gas_price().await?;
        let l1_fee = self.estimate_l1_fee(tx).await?;
        
        Ok(l2_gas * l2_gas_price + l1_fee)
    }
    
    async fn estimate_l1_fee(&self, _tx: &TypedTransaction) -> Result<U256> {
        // Simplified L1 fee calculation
        Ok(U256::from(1000000)) // ~$1 in wei
    }
}
