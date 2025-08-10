pub mod inventory_manager;
pub mod bridge_aggregator;

use anyhow::Result;
use ethers::prelude::*;
use std::collections::HashMap;

#[derive(Clone, Copy, Debug, Hash, Eq, PartialEq)]
pub enum ChainId {
    Ethereum = 1,
    Arbitrum = 42161,
    Optimism = 10,
    Polygon = 137,
    BSC = 56,
    Base = 8453,
}

pub struct CrossChainRouter {
    chains: HashMap<ChainId, ChainConfig>,
}

pub struct ChainConfig {
    pub rpc_url: String,
    pub chain_id: u64,
    pub name: String,
}
