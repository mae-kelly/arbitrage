use anyhow::Result;
use ethers::prelude::*;
use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Deserialize, Serialize};
use tokio_tungstenite::{connect_async, tungstenite::Message};
use futures::{StreamExt, SinkExt};

pub struct OrderbookScanner {
    uniswap_v3_pools: Arc<RwLock<Vec<PoolState>>>,
    sushiswap_pools: Arc<RwLock<Vec<PoolState>>>,
    pancakeswap_pools: Arc<RwLock<Vec<PoolState>>>,
    providers: Vec<Arc<Provider<Ws>>>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PoolState {
    pub address: String,
    pub token0: String,
    pub token1: String,
    pub reserve0: U256,
    pub reserve1: U256,
    pub sqrt_price_x96: U256,
    pub liquidity: u128,
    pub fee: u32,
}

impl OrderbookScanner {
    pub async fn new() -> Result<Self> {
        let eth_provider = Provider::<Ws>::connect("wss://eth-mainnet.g.alchemy.com/v2/demo").await?;
        let bsc_provider = Provider::<Ws>::connect("wss://bsc-dataseed.binance.org/").await?;
        let polygon_provider = Provider::<Ws>::connect("wss://polygon-mainnet.g.alchemy.com/v2/demo").await?;
        
        Ok(Self {
            uniswap_v3_pools: Arc::new(RwLock::new(Vec::new())),
            sushiswap_pools: Arc::new(RwLock::new(Vec::new())),
            pancakeswap_pools: Arc::new(RwLock::new(Vec::new())),
            providers: vec![
                Arc::new(eth_provider),
                Arc::new(bsc_provider),
                Arc::new(polygon_provider),
            ],
        })
    }

    pub async fn scan(&self) -> Result<Vec<(String, String, f64)>> {
        let mut opportunities = Vec::new();
        
        self.update_pool_states().await?;
        
        let uniswap_pools = self.uniswap_v3_pools.read().await;
        let sushi_pools = self.sushiswap_pools.read().await;
        
        for uni_pool in uniswap_pools.iter() {
            for sushi_pool in sushi_pools.iter() {
                if uni_pool.token0 == sushi_pool.token0 && uni_pool.token1 == sushi_pool.token1 {
                    let spread = self.calculate_spread(uni_pool, sushi_pool)?;
                    if spread.abs() > 0.002 {
                        opportunities.push((
                            format!("uniswap-{}", uni_pool.address),
                            format!("sushi-{}", sushi_pool.address),
                            spread,
                        ));
                    }
                }
            }
        }
        
        Ok(opportunities)
    }

    async fn update_pool_states(&self) -> Result<()> {
        let uniswap_factory = Address::from_str("0x1F98431c8aD98523631AE4a59f267346ea31F984")?;
        let provider = &self.providers[0];
        
        let filter = Filter::new()
            .address(uniswap_factory)
            .event("PoolCreated(address,address,uint24,int24,address)")
            .from_block(BlockNumber::Latest);
        
        let logs = provider.get_logs(&filter).await?;
        
        for log in logs {
            if log.topics.len() >= 3 {
                let pool_address = Address::from(log.topics[3]);
                self.fetch_pool_state(pool_address).await?;
            }
        }
        
        Ok(())
    }

    async fn fetch_pool_state(&self, pool_address: Address) -> Result<PoolState> {
        let provider = &self.providers[0];
        
        let slot0_sig = "0x3850c7bd";
        let liquidity_sig = "0x1a686502";
        
        let slot0_call = provider.call(
            &TransactionRequest::new().to(pool_address).data(hex::decode(&slot0_sig[2..])?),
            None
        ).await?;
        
        Ok(PoolState {
            address: format!("{:?}", pool_address),
            token0: String::new(),
            token1: String::new(),
            reserve0: U256::zero(),
            reserve1: U256::zero(),
            sqrt_price_x96: U256::zero(),
            liquidity: 0,
            fee: 3000,
        })
    }

    fn calculate_spread(&self, pool_a: &PoolState, pool_b: &PoolState) -> Result<f64> {
        let price_a = pool_a.sqrt_price_x96.as_u128() as f64 / (1u128 << 96) as f64;
        let price_b = pool_b.sqrt_price_x96.as_u128() as f64 / (1u128 << 96) as f64;
        
        Ok((price_a - price_b) / price_a)
    }
}
