use ethers::prelude::*;
use std::sync::Arc;
use parking_lot::RwLock;

use crate::Config;
use crate::arbitrage::Opportunity;

pub struct TradeExecutor {
    client: Arc<SignerMiddleware<Provider<Http>, LocalWallet>>,
    config: Arc<Config>,
    nonce_tracker: Arc<RwLock<U256>>,
    gas_oracle: Arc<RwLock<U256>>,
}

impl TradeExecutor {
    pub fn new(client: Arc<SignerMiddleware<Provider<Http>, LocalWallet>>, config: Arc<Config>) -> Self {
        Self {
            client,
            config,
            nonce_tracker: Arc::new(RwLock::new(U256::zero())),
            gas_oracle: Arc::new(RwLock::new(U256::from(30) * U256::from(10).pow(U256::from(9)))),
        }
    }
    
    pub async fn execute_trade(&self, opportunity: &Opportunity) -> anyhow::Result<H256> {
        if self.config.mode == "test" {
            return Ok(H256::random());
        }
        
        let nonce = self.get_next_nonce().await?;
        let gas_price = self.get_optimal_gas_price().await?;
        
        let router_address = self.get_router_address(&opportunity.dex_buy)?;
        let swap_data = self.encode_swap_data(opportunity)?;
        
        let tx = TransactionRequest::new()
            .to(router_address)
            .data(swap_data)
            .value(U256::zero())
            .gas(U256::from(350000))
            .gas_price(gas_price)
            .nonce(nonce);
        
        let pending_tx = self.client.send_transaction(tx, None).await?;
        Ok(pending_tx.tx_hash())
    }
    
    async fn get_next_nonce(&self) -> anyhow::Result<U256> {
        let address = self.config.wallet_address.parse::<Address>()?;
        let nonce = self.client.get_transaction_count(address, None).await?;
        
        let mut tracker = self.nonce_tracker.write();
        if nonce > *tracker {
            *tracker = nonce;
        }
        let current_nonce = *tracker;
        *tracker = *tracker + 1;
        
        Ok(current_nonce)
    }
    
    async fn get_optimal_gas_price(&self) -> anyhow::Result<U256> {
        let base_fee = self.client.get_gas_price().await?;
        let max_gas = U256::from(self.config.max_gas_gwei) * U256::from(10).pow(U256::from(9));
        
        let optimal = if self.config.flashbots_enabled {
            base_fee * U256::from(110) / U256::from(100)
        } else {
            base_fee * U256::from(105) / U256::from(100)
        };
        
        let gas_price = optimal.min(max_gas);
        *self.gas_oracle.write() = gas_price;
        
        Ok(gas_price)
    }
    
    fn get_router_address(&self, dex: &str) -> anyhow::Result<Address> {
        let address = match dex {
            "uniswap_v2" => "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
            "sushiswap" => "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F",
            "uniswap_v3" => "0xE592427A0AEce92De3Edee1F18E0157C05861564",
            "balancer" => "0xBA12222222228d8Ba445958a75a0704d566BF2C8",
            "curve" => "0x99a58482BD75cbab83b27EC03CA68fF489b5788f",
            _ => "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
        };
        
        Ok(address.parse()?)
    }
    
    fn encode_swap_data(&self, opportunity: &Opportunity) -> anyhow::Result<Bytes> {
        let path = vec![opportunity.token_in, opportunity.token_out];
        let deadline = U256::from(chrono::Utc::now().timestamp() + 300);
        
        let calldata = ethers::abi::encode(&[
            ethers::abi::Token::Uint(opportunity.amount_in.into()),
            ethers::abi::Token::Uint(opportunity.amount_out.into()),
            ethers::abi::Token::Array(path.iter().map(|a| ethers::abi::Token::Address(a.0.into())).collect()),
            ethers::abi::Token::Address(self.config.wallet_address.parse::<Address>().unwrap().into()),
            ethers::abi::Token::Uint(deadline.into()),
        ]);
        
        Ok(calldata.into())
    }
    
    pub async fn batch_execute(&self, opportunities: Vec<Opportunity>) -> Vec<anyhow::Result<H256>> {
        let mut results = Vec::new();
        
        for opportunity in opportunities {
            results.push(self.execute_trade(&opportunity).await);
        }
        
        results
    }
    
    pub async fn estimate_gas(&self, opportunity: &Opportunity) -> anyhow::Result<U256> {
        let router_address = self.get_router_address(&opportunity.dex_buy)?;
        let swap_data = self.encode_swap_data(opportunity)?;
        
        let tx = TransactionRequest::new()
            .to(router_address)
            .data(swap_data)
            .value(U256::zero());
        
        let gas_estimate = self.client.estimate_gas(&tx.into(), None).await?;
        Ok(gas_estimate)
    }
}