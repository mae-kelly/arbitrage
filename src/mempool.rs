use ethers::prelude::*;
use std::sync::Arc;
use dashmap::DashMap;
use tokio::sync::mpsc;

use crate::arbitrage::Opportunity;

pub struct MempoolMonitor {
    provider: Arc<Provider<Http>>,
    pending_txs: Arc<DashMap<H256, Transaction>>,
}

impl MempoolMonitor {
    pub fn new(provider: Arc<Provider<Http>>) -> Self {
        Self {
            provider,
            pending_txs: Arc::new(DashMap::new()),
        }
    }
    
    pub async fn start_monitoring(&self, opportunities: Arc<DashMap<String, Opportunity>>) -> anyhow::Result<()> {
        let (tx, mut rx) = mpsc::unbounded_channel();
        
        let provider = self.provider.clone();
        let pending_txs = self.pending_txs.clone();
        
        tokio::spawn(async move {
            loop {
                if let Ok(block) = provider.get_block(BlockNumber::Pending).await {
                    if let Some(block) = block {
                        for tx_hash in block.transactions {
                            if let Ok(Some(transaction)) = provider.get_transaction(tx_hash).await {
                                pending_txs.insert(tx_hash, transaction.clone());
                                let _ = tx.send(transaction);
                            }
                        }
                    }
                }
                tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
            }
        });
        
        while let Some(tx) = rx.recv().await {
            if let Some(opportunity) = self.analyze_transaction(&tx).await {
                let key = format!("{:?}-{}", tx.hash, chrono::Utc::now().timestamp_nanos_opt().unwrap_or(0));
                opportunities.insert(key, opportunity);
            }
        }
        
        Ok(())
    }
    
    async fn analyze_transaction(&self, tx: &Transaction) -> Option<Opportunity> {
        if tx.input.len() < 4 {
            return None;
        }
        
        let method_id = &tx.input[0..4];
        
        match method_id {
            [0xa9, 0x05, 0x9c, 0xbb] => self.analyze_swap(tx, "uniswap_v2").await,
            [0x38, 0xed, 0x17, 0x39] => self.analyze_swap(tx, "uniswap_v2").await,
            [0x7f, 0xf3, 0x6a, 0xb5] => self.analyze_swap(tx, "uniswap_v2").await,
            [0x41, 0x4b, 0xf3, 0x89] => self.analyze_swap(tx, "uniswap_v3").await,
            [0x52, 0xbf, 0xbe, 0x29] => self.analyze_swap(tx, "balancer").await,
            _ => None,
        }
    }
    
    async fn analyze_swap(&self, tx: &Transaction, dex: &str) -> Option<Opportunity> {
        let decoded = self.decode_swap_data(&tx.input, dex)?;
        
        let (token_in, token_out, amount_in, min_amount_out) = decoded;
        
        let opposite_dex = match dex {
            "uniswap_v2" => "sushiswap",
            "sushiswap" => "uniswap_v2",
            "uniswap_v3" => "balancer",
            "balancer" => "uniswap_v3",
            _ => "uniswap_v2",
        };
        
        Some(Opportunity {
            token_in,
            token_out,
            amount_in,
            amount_out: min_amount_out,
            dex_buy: dex.to_string(),
            dex_sell: opposite_dex.to_string(),
            gas_price: tx.gas_price.unwrap_or_default(),
            block_number: tx.block_number.unwrap_or_default().as_u64(),
            timestamp: chrono::Utc::now().timestamp() as u64,
            profit_wei: U256::zero(),
            confidence: 0.5,
        })
    }
    
    fn decode_swap_data(&self, input: &Bytes, dex: &str) -> Option<(Address, Address, U256, U256)> {
        if input.len() < 136 {
            return None;
        }
        
        match dex {
            "uniswap_v2" | "sushiswap" => {
                let amount_in = U256::from_big_endian(&input[4..36]);
                let amount_out_min = U256::from_big_endian(&input[36..68]);
                let path_offset = U256::from_big_endian(&input[68..100]).as_usize();
                
                if input.len() < path_offset + 68 {
                    return None;
                }
                
                let token_in = Address::from_slice(&input[path_offset + 12..path_offset + 32]);
                let token_out = Address::from_slice(&input[path_offset + 44..path_offset + 64]);
                
                Some((token_in, token_out, amount_in, amount_out_min))
            }
            "uniswap_v3" => {
                let token_in = Address::from_slice(&input[16..36]);
                let token_out = Address::from_slice(&input[48..68]);
                let amount_in = U256::from_big_endian(&input[68..100]);
                let amount_out_min = U256::from_big_endian(&input[100..132]);
                
                Some((token_in, token_out, amount_in, amount_out_min))
            }
            "balancer" => {
                let token_in = Address::from_slice(&input[44..64]);
                let token_out = Address::from_slice(&input[76..96]);
                let amount_in = U256::from_big_endian(&input[96..128]);
                let amount_out_min = U256::from_big_endian(&input[128..160]);
                
                Some((token_in, token_out, amount_in, amount_out_min))
            }
            _ => None,
        }
    }
    
    pub async fn get_pending_transactions(&self) -> Vec<Transaction> {
        self.pending_txs
            .iter()
            .map(|entry| entry.value().clone())
            .collect()
    }
    
    pub fn clear_old_transactions(&self, current_block: u64) {
        self.pending_txs.retain(|_, tx| {
            tx.block_number
                .map(|bn| bn.as_u64() >= current_block.saturating_sub(10))
                .unwrap_or(true)
        });
    }
}