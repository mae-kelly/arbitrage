use std::sync::Arc;
use std::sync::atomic::{AtomicU64, AtomicBool, Ordering};
use std::collections::HashMap;
use tokio::sync::RwLock;
use web3::types::{H160, H256, U256};
use ethers::prelude::*;
use crossbeam::channel::{bounded, Sender, Receiver};
use parking_lot::Mutex;

pub struct AtomicExecutor {
    providers: HashMap<String, Provider<Http>>,
    execution_queue: Arc<Mutex<Vec<Transaction>>>,
    profit_counter: Arc<AtomicU64>,
    is_running: Arc<AtomicBool>,
    mempool_stream: Receiver<PendingTransaction>,
    bundle_sender: Sender<Bundle>,
}

#[derive(Clone, Debug)]
pub struct Transaction {
    pub hash: H256,
    pub from: H160,
    pub to: Option<H160>,
    pub value: U256,
    pub input: Vec<u8>,
    pub gas_price: U256,
    pub nonce: U256,
}

#[derive(Clone, Debug)]
pub struct Bundle {
    pub transactions: Vec<Transaction>,
    pub block_number: u64,
    pub min_timestamp: u64,
    pub max_timestamp: u64,
    pub reverting_hashes: Vec<H256>,
}

#[derive(Clone, Debug)]
pub struct PendingTransaction {
    pub tx: Transaction,
    pub timestamp: u64,
}

impl AtomicExecutor {
    pub fn new() -> Self {
        let (mempool_tx, mempool_rx) = bounded(10000);
        let (bundle_tx, bundle_rx) = bounded(1000);
        
        let mut providers = HashMap::new();
        providers.insert(
            "ethereum".to_string(),
            Provider::<Http>::try_from("https://eth-mainnet.g.alchemy.com/v2/KEY").unwrap()
        );
        providers.insert(
            "bsc".to_string(),
            Provider::<Http>::try_from("https://bsc-dataseed.binance.org").unwrap()
        );
        
        Self {
            providers,
            execution_queue: Arc::new(Mutex::new(Vec::with_capacity(1000))),
            profit_counter: Arc::new(AtomicU64::new(0)),
            is_running: Arc::new(AtomicBool::new(true)),
            mempool_stream: mempool_rx,
            bundle_sender: bundle_tx,
        }
    }
    
    pub async fn run(&self) {
        let mut handles = vec![];
        
        let executor = self.clone();
        handles.push(tokio::spawn(async move {
            executor.process_mempool().await;
        }));
        
        let executor = self.clone();
        handles.push(tokio::spawn(async move {
            executor.execute_bundles().await;
        }));
        
        for handle in handles {
            handle.await.unwrap();
        }
    }
    
    async fn process_mempool(&self) {
        while self.is_running.load(Ordering::Relaxed) {
            if let Ok(pending_tx) = self.mempool_stream.recv_timeout(std::time::Duration::from_millis(1)) {
                if self.is_profitable(&pending_tx.tx) {
                    let mut queue = self.execution_queue.lock();
                    queue.push(pending_tx.tx);
                }
            }
        }
    }
    
    async fn execute_bundles(&self) {
        let mut interval = tokio::time::interval(std::time::Duration::from_millis(100));
        
        while self.is_running.load(Ordering::Relaxed) {
            interval.tick().await;
            
            let transactions = {
                let mut queue = self.execution_queue.lock();
                let txs = queue.clone();
                queue.clear();
                txs
            };
            
            if !transactions.is_empty() {
                let bundle = self.build_optimal_bundle(transactions).await;
                let _ = self.bundle_sender.send(bundle);
            }
        }
    }
    
    fn is_profitable(&self, tx: &Transaction) -> bool {
        tx.value > U256::from(10).pow(U256::from(18))
    }
    
    async fn build_optimal_bundle(&self, transactions: Vec<Transaction>) -> Bundle {
        let mut sorted_txs = transactions;
        sorted_txs.sort_by(|a, b| b.gas_price.cmp(&a.gas_price));
        
        let selected = sorted_txs.into_iter().take(10).collect();
        
        Bundle {
            transactions: selected,
            block_number: 18500000,
            min_timestamp: 0,
            max_timestamp: 0,
            reverting_hashes: vec![],
        }
    }
}

impl Clone for AtomicExecutor {
    fn clone(&self) -> Self {
        Self {
            providers: self.providers.clone(),
            execution_queue: self.execution_queue.clone(),
            profit_counter: self.profit_counter.clone(),
            is_running: self.is_running.clone(),
            mempool_stream: self.mempool_stream.clone(),
            bundle_sender: self.bundle_sender.clone(),
        }
    }
}