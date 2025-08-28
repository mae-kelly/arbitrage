// core/rust_ws/src/price_feed.rs
use ethers::prelude::*;
use std::sync::Arc;
use tokio::sync::RwLock;
use dashmap::DashMap;
use std::time::{Duration, Instant};

#[derive(Clone, Debug)]
pub struct PriceData {
    pub token0: Address,
    pub token1: Address,
    pub price: U256,
    pub liquidity: U256,
    pub timestamp: Instant,
    pub dex: String,
    pub chain_id: u64,
}

pub struct PriceFeedAggregator {
    prices: Arc<DashMap<String, PriceData>>,
    providers: Arc<RwLock<Vec<Arc<Provider<Ws>>>>>,
}

impl PriceFeedAggregator {
    pub async fn new() -> Self {
        let providers = vec![
            Arc::new(Provider::<Ws>::connect("wss://eth-mainnet.g.alchemy.com/v2/demo").await.unwrap()),
            Arc::new(Provider::<Ws>::connect("wss://arb-mainnet.g.alchemy.com/v2/demo").await.unwrap()),
            Arc::new(Provider::<Ws>::connect("wss://opt-mainnet.g.alchemy.com/v2/demo").await.unwrap()),
            Arc::new(Provider::<Ws>::connect("wss://polygon-mainnet.g.alchemy.com/v2/demo").await.unwrap()),
            Arc::new(Provider::<Ws>::connect("wss://base-mainnet.g.alchemy.com/v2/demo").await.unwrap()),
        ];
        
        Self {
            prices: Arc::new(DashMap::new()),
            providers: Arc::new(RwLock::new(providers)),
        }
    }
    
    pub async fn start_feeds(&self) {
        let uniswap_v2_pairs = vec![
            ("0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc".parse::<Address>().unwrap(), 1u64),
            ("0xDFC14d2Af169B0D36C4EFF567Ada9b2E0CAE044f".parse::<Address>().unwrap(), 1u64),
            ("0xBb2b8038a1640196FbE3e38816F3e67Cba72D940".parse::<Address>().unwrap(), 1u64),
        ];
        
        let uniswap_v3_pools = vec![
            ("0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8".parse::<Address>().unwrap(), 1u64),
            ("0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640".parse::<Address>().unwrap(), 1u64),
            ("0x4e68Ccd3E89f51C3074ca5072bbAC773960dFa36".parse::<Address>().unwrap(), 1u64),
        ];
        
        let sushi_pairs = vec![
            ("0x06da0fd433C1A5d7a4faa01111c044910A184553".parse::<Address>().unwrap(), 1u64),
            ("0x397FF1542f962076d0BFE58eA045FfA2d347ACa0".parse::<Address>().unwrap(), 1u64),
        ];
        
        for (pair, chain_id) in uniswap_v2_pairs {
            self.monitor_uniswap_v2_pair(pair, chain_id).await;
        }
        
        for (pool, chain_id) in uniswap_v3_pools {
            self.monitor_uniswap_v3_pool(pool, chain_id).await;
        }
        
        for (pair, chain_id) in sushi_pairs {
            self.monitor_sushi_pair(pair, chain_id).await;
        }
    }
    
    async fn monitor_uniswap_v2_pair(&self, pair_address: Address, chain_id: u64) {
        let providers = self.providers.read().await;
        let provider = providers[0].clone();
        
        let pair_abi = ethers::abi::parse_abi(&[
            "function getReserves() external view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast)",
            "function token0() external view returns (address)",
            "function token1() external view returns (address)",
        ]).unwrap();
        
        let pair = Contract::new(pair_address, pair_abi.clone(), provider.clone());
        
        tokio::spawn(async move {
            loop {
                if let Ok(reserves) = pair.method::<_, (U256, U256, u32)>("getReserves", ()).unwrap().call().await {
                    let token0: Address = pair.method("token0", ()).unwrap().call().await.unwrap();
                    let token1: Address = pair.method("token1", ()).unwrap().call().await.unwrap();
                    
                    let price = reserves.0 * U256::from(10).pow(U256::from(18)) / reserves.1;
                    
                    let price_data = PriceData {
                        token0,
                        token1,
                        price,
                        liquidity: reserves.0 + reserves.1,
                        timestamp: Instant::now(),
                        dex: "UniswapV2".to_string(),
                        chain_id,
                    };
                    
                    println!("UniV2 {} Price: {}", pair_address, price);
                }
                tokio::time::sleep(Duration::from_millis(100)).await;
            }
        });
    }
    
    async fn monitor_uniswap_v3_pool(&self, pool_address: Address, chain_id: u64) {
        let providers = self.providers.read().await;
        let provider = providers[0].clone();
        
        let pool_abi = ethers::abi::parse_abi(&[
            "function slot0() external view returns (uint160 sqrtPriceX96, int24 tick, uint16 observationIndex, uint16 observationCardinality, uint16 observationCardinalityNext, uint8 feeProtocol, bool unlocked)",
            "function liquidity() external view returns (uint128)",
            "function token0() external view returns (address)",
            "function token1() external view returns (address)",
        ]).unwrap();
        
        let pool = Contract::new(pool_address, pool_abi.clone(), provider.clone());
        
        tokio::spawn(async move {
            loop {
                if let Ok(slot0) = pool.method::<_, (U256, i32, u16, u16, u16, u8, bool)>("slot0", ()).unwrap().call().await {
                    let token0: Address = pool.method("token0", ()).unwrap().call().await.unwrap();
                    let token1: Address = pool.method("token1", ()).unwrap().call().await.unwrap();
                    let liquidity: u128 = pool.method("liquidity", ()).unwrap().call().await.unwrap();
                    
                    let sqrt_price = slot0.0;
                    let price = sqrt_price.pow(U256::from(2)) / U256::from(2).pow(U256::from(192));
                    
                    let price_data = PriceData {
                        token0,
                        token1,
                        price,
                        liquidity: U256::from(liquidity),
                        timestamp: Instant::now(),
                        dex: "UniswapV3".to_string(),
                        chain_id,
                    };
                    
                    println!("UniV3 {} Price: {}", pool_address, price);
                }
                tokio::time::sleep(Duration::from_millis(100)).await;
            }
        });
    }
    
    async fn monitor_sushi_pair(&self, pair_address: Address, chain_id: u64) {
        let providers = self.providers.read().await;
        let provider = providers[0].clone();
        
        let pair_abi = ethers::abi::parse_abi(&[
            "function getReserves() external view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast)",
            "function token0() external view returns (address)",
            "function token1() external view returns (address)",
        ]).unwrap();
        
        let pair = Contract::new(pair_address, pair_abi.clone(), provider.clone());
        
        tokio::spawn(async move {
            loop {
                if let Ok(reserves) = pair.method::<_, (U256, U256, u32)>("getReserves", ()).unwrap().call().await {
                    let token0: Address = pair.method("token0", ()).unwrap().call().await.unwrap();
                    let token1: Address = pair.method("token1", ()).unwrap().call().await.unwrap();
                    
                    let price = reserves.0 * U256::from(10).pow(U256::from(18)) / reserves.1;
                    
                    let price_data = PriceData {
                        token0,
                        token1,
                        price,
                        liquidity: reserves.0 + reserves.1,
                        timestamp: Instant::now(),
                        dex: "SushiSwap".to_string(),
                        chain_id,
                    };
                    
                    println!("Sushi {} Price: {}", pair_address, price);
                }
                tokio::time::sleep(Duration::from_millis(100)).await;
            }
        });
    }
    
    pub async fn find_arbitrage(&self) -> Vec<(PriceData, PriceData, U256)> {
        let mut opportunities = Vec::new();
        
        for entry1 in self.prices.iter() {
            for entry2 in self.prices.iter() {
                if entry1.dex != entry2.dex 
                    && entry1.token0 == entry2.token0 
                    && entry1.token1 == entry2.token1
                    && entry1.chain_id == entry2.chain_id {
                    
                    let price_diff = if entry1.price > entry2.price {
                        entry1.price - entry2.price
                    } else {
                        entry2.price - entry1.price
                    };
                    
                    let threshold = entry1.price / U256::from(200);
                    if price_diff > threshold {
                        opportunities.push((entry1.clone(), entry2.clone(), price_diff));
                    }
                }
            }
        }
        
        opportunities
    }
}