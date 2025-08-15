//! Blockchain integration module

pub mod ethereum;
pub mod arbitrum;
pub mod optimism;
pub mod bridges;

use anyhow::Result;

pub struct MultiChainClient {
    pub ethereum: ethereum::EthereumClient,
    pub arbitrum: arbitrum::ArbitrumClient,
    pub bridge_router: bridges::BridgeRouter,
}

impl MultiChainClient {
    pub async fn new() -> Result<Self> {
        let ethereum = ethereum::EthereumClient::new(
            "wss://eth-mainnet.g.alchemy.com/v2/your-key",
            "your-private-key"
        ).await?;
        
        let arbitrum = arbitrum::ArbitrumClient::new().await?;
        let bridge_router = bridges::BridgeRouter::new();
        
        Ok(Self {
            ethereum,
            arbitrum,
            bridge_router,
        })
    }
}
