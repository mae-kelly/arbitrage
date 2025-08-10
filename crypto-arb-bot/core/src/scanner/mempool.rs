use anyhow::Result;
use ethers::prelude::*;
use std::sync::Arc;
use tokio::sync::RwLock;
use dashmap::DashMap;

pub struct MempoolScanner {
    providers: Vec<Arc<Provider<Ws>>>,
    pending_txs: Arc<DashMap<H256, Transaction>>,
    filters: Arc<RwLock<Vec<MempoolFilter>>>,
}

#[derive(Clone)]
struct MempoolFilter {
    token_address: Option<Address>,
    min_value: U256,
    dex_addresses: Vec<Address>,
}

impl MempoolScanner {
    pub async fn new() -> Result<Self> {
        let eth_ws = Provider::<Ws>::connect("wss://eth-mainnet.g.alchemy.com/v2/demo").await?;
        let arb_ws = Provider::<Ws>::connect("wss://arb-mainnet.g.alchemy.com/v2/demo").await?;
        
        let uniswap_v3 = Address::from_str("0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45")?;
        let sushiswap = Address::from_str("0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F")?;
        
        let filters = vec![
            MempoolFilter {
                token_address: None,
                min_value: U256::from(10000000000000000000u128),
                dex_addresses: vec![uniswap_v3, sushiswap],
            }
        ];
        
        Ok(Self {
            providers: vec![Arc::new(eth_ws), Arc::new(arb_ws)],
            pending_txs: Arc::new(DashMap::new()),
            filters: Arc::new(RwLock::new(filters)),
        })
    }

    pub async fn scan(&self) -> Result<Vec<Transaction>> {
        let mut relevant_txs = Vec::new();
        
        for provider in &self.providers {
            let mut stream = provider.subscribe_pending_txs().await?;
            
            while let Some(tx_hash) = stream.next().await {
                if let Some(tx) = provider.get_transaction(tx_hash).await? {
                    if self.is_relevant(&tx).await? {
                        self.pending_txs.insert(tx.hash, tx.clone());
                        relevant_txs.push(tx);
                    }
                }
            }
        }
        
        Ok(relevant_txs)
    }

    async fn is_relevant(&self, tx: &Transaction) -> Result<bool> {
        let filters = self.filters.read().await;
        
        for filter in filters.iter() {
            if tx.value >= filter.min_value {
                if let Some(to) = tx.to {
                    if filter.dex_addresses.contains(&to) {
                        return Ok(true);
                    }
                }
            }
        }
        
        Ok(false)
    }

    pub async fn simulate_transaction(&self, tx: &Transaction) -> Result<SimulationResult> {
        let provider = &self.providers[0];
        
        let call_request = CallRequest {
            from: tx.from,
            to: tx.to,
            gas: tx.gas,
            gas_price: tx.gas_price,
            value: Some(tx.value),
            data: Some(tx.input.clone()),
            ..Default::default()
        };
        
        let result = provider.call(&call_request.into(), None).await?;
        
        Ok(SimulationResult {
            success: !result.is_empty(),
            return_data: result,
        })
    }
}

#[derive(Debug)]
pub struct SimulationResult {
    pub success: bool,
    pub return_data: Bytes,
}
