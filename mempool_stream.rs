use ethers::prelude::*;
use std::sync::Arc;
use tokio::sync::RwLock;
use futures_util::StreamExt;
use serde::{Deserialize, Serialize};
use crossbeam::channel::{unbounded, Sender};
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MempoolTransaction {
    pub hash: H256,
    pub from: Address,
    pub to: Option<Address>,
    pub value: U256,
    pub gas_price: U256,
    pub gas: U256,
    pub input: Bytes,
    pub nonce: U256,
    pub timestamp: u64,
}

pub struct MempoolStream {
    provider: Arc<Provider<Ws>>,
    tx_sender: Sender<MempoolTransaction>,
    interesting_addresses: Arc<RwLock<HashMap<Address, String>>>,
    min_value_threshold: U256,
}

impl MempoolStream {
    pub async fn new(ws_url: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let provider = Provider::<Ws>::connect(ws_url).await?;
        let (tx_sender, _rx) = unbounded();
        
        let mut interesting_addresses = HashMap::new();
        interesting_addresses.insert(
            "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D".parse()?,
            "Uniswap V2 Router".to_string()
        );
        interesting_addresses.insert(
            "0xE592427A0AEce92De3Edee1F18E0157C05861564".parse()?,
            "Uniswap V3 Router".to_string()
        );
        interesting_addresses.insert(
            "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2".parse()?,
            "Aave V3".to_string()
        );
        
        Ok(Self {
            provider: Arc::new(provider),
            tx_sender,
            interesting_addresses: Arc::new(RwLock::new(interesting_addresses)),
            min_value_threshold: U256::from(10).pow(U256::from(18)),
        })
    }
    
    pub async fn start_monitoring(&self) -> Result<(), Box<dyn std::error::Error>> {
        let mut stream = self.provider.subscribe_pending_txs().await?;
        
        while let Some(tx_hash) = stream.next().await {
            let provider = self.provider.clone();
            let tx_sender = self.tx_sender.clone();
            let interesting_addresses = self.interesting_addresses.clone();
            let min_value = self.min_value_threshold;
            
            tokio::spawn(async move {
                if let Ok(Some(tx)) = provider.get_transaction(tx_hash).await {
                    if Self::is_interesting(&tx, &interesting_addresses, min_value).await {
                        let mempool_tx = Self::convert_transaction(tx);
                        let _ = tx_sender.send(mempool_tx);
                    }
                }
            });
        }
        
        Ok(())
    }
    
    async fn is_interesting(
        tx: &Transaction,
        addresses: &Arc<RwLock<HashMap<Address, String>>>,
        min_value: U256
    ) -> bool {
        if tx.value > min_value {
            return true;
        }
        
        if let Some(to) = tx.to {
            let addrs = addresses.read().await;
            if addrs.contains_key(&to) {
                return true;
            }
        }
        
        if tx.gas_price > U256::from(100) * U256::from(10).pow(U256::from(9)) {
            return true;
        }
        
        false
    }
    
    fn convert_transaction(tx: Transaction) -> MempoolTransaction {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();
        
        MempoolTransaction {
            hash: tx.hash,
            from: tx.from,
            to: tx.to,
            value: tx.value,
            gas_price: tx.gas_price.unwrap_or_default(),
            gas: tx.gas,
            input: tx.input,
            nonce: tx.nonce,
            timestamp,
        }
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let ws_urls = vec![
        "wss://mainnet.infura.io/ws/v3/YOUR_KEY",
        "wss://eth-mainnet.g.alchemy.com/v2/YOUR_KEY",
    ];
    
    let mut handles = vec![];
    
    for url in ws_urls {
        let handle = tokio::spawn(async move {
            match MempoolStream::new(&url).await {
                Ok(stream) => {
                    if let Err(e) = stream.start_monitoring().await {
                        eprintln!("Monitoring error: {}", e);
                    }
                }
                Err(e) => eprintln!("Connection error: {}", e),
            }
        });
        handles.push(handle);
    }
    
    for handle in handles {
        handle.await?;
    }
    
    Ok(())
}