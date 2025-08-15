//! Ethereum blockchain integration with ethers-rs

use ethers::prelude::*;
use anyhow::Result;
use std::sync::Arc;
use tokio::sync::RwLock;

pub mod contracts;
pub mod flash_loans;
pub mod gas_optimization;
pub mod mev_protection;

#[derive(Clone)]
pub struct EthereumClient {
    provider: Arc<Provider<Ws>>,
    signer: Arc<SignerMiddleware<Provider<Ws>, LocalWallet>>,
    chain_id: u64,
    contracts: contracts::ContractRegistry,
}

impl EthereumClient {
    pub async fn new(ws_url: &str, private_key: &str) -> Result<Self> {
        let provider = Provider::<Ws>::connect(ws_url).await?;
        let chain_id = provider.get_chainid().await?.as_u64();
        
        let wallet = private_key.parse::<LocalWallet>()?
            .with_chain_id(chain_id);
        
        let signer = Arc::new(SignerMiddleware::new(
            provider.clone(),
            wallet
        ));
        
        let contracts = contracts::ContractRegistry::new(signer.clone()).await?;
        
        Ok(Self {
            provider: Arc::new(provider),
            signer,
            chain_id,
            contracts,
        })
    }
    
    pub async fn execute_flash_loan_arbitrage(
        &self,
        token: Address,
        amount: U256,
        exchanges: Vec<Address>,
        calldata: Vec<Bytes>,
    ) -> Result<TxHash> {
        self.contracts.arbitrage_contract
            .execute_arbitrage(token, amount, exchanges, calldata)
            .send()
            .await?
            .await?
            .ok_or_else(|| anyhow::anyhow!("Transaction failed"))?
            .transaction_hash
            .pipe(Ok)
    }
    
    pub async fn get_gas_price(&self) -> Result<U256> {
        self.provider.get_gas_price().await.map_err(Into::into)
    }
    
    pub async fn estimate_gas(&self, tx: &TypedTransaction) -> Result<U256> {
        self.provider.estimate_gas(tx).await.map_err(Into::into)
    }
}
