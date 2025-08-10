use anyhow::Result;
use ethers::prelude::*;
use std::sync::Arc;

pub struct ProductionExecutor {
    wallet: LocalWallet,
    providers: Vec<Arc<Provider<Http>>>,
    gas_oracle: GasOracle,
}

impl ProductionExecutor {
    pub async fn new(private_key: &str, rpc_urls: Vec<&str>) -> Result<Self> {
        let wallet = private_key.parse()?;
        let mut providers = Vec::new();
        
        for url in rpc_urls {
            providers.push(Arc::new(Provider::try_from(url)?));
        }
        
        Ok(Self {
            wallet,
            providers,
            gas_oracle: GasOracle::new(),
        })
    }

    pub async fn execute_flash_arbitrage(&self, token: Address, amount: U256, dex_a: Address, dex_b: Address) -> Result<H256> {
        let contract_addr: Address = std::env::var("FLASH_LOAN_CONTRACT")?.parse()?;
        let params = ethers::abi::encode(&[
            ethers::abi::Token::Address(dex_a),
            ethers::abi::Token::Address(dex_b),
            ethers::abi::Token::Uint(U256::from(1000))
        ]);
        
        let client = SignerMiddleware::new(self.providers[0].clone(), self.wallet.clone());
        let abi = r#"[{"inputs":[{"name":"asset","type":"address"},{"name":"amount","type":"uint256"},{"name":"params","type":"bytes"}],"name":"executeArbitrage","type":"function"}]"#;
        let contract = Contract::new(contract_addr, serde_json::from_str(abi)?, Arc::new(client));

        let gas_price = self.gas_oracle.get_fast_gas_price().await?;
        let tx = contract
            .method("executeArbitrage", (token, amount, params))?
            .gas_price(gas_price)
            .send().await?;
        Ok(tx.tx_hash())
    }

    pub async fn execute_cross_chain(&self, src_amount: U256, dst_chain: u16, min_profit: U256) -> Result<Vec<H256>> {
        let mut txs = Vec::new();
        
        let bridge_tx = self.bridge_to_l2(src_amount, dst_chain).await?;
        txs.push(bridge_tx);
        
        tokio::time::sleep(std::time::Duration::from_secs(300)).await;
        
        let arb_tx = self.execute_l2_arbitrage(dst_chain, src_amount, min_profit).await?;
        txs.push(arb_tx);
        
        Ok(txs)
    }

    async fn bridge_to_l2(&self, amount: U256, dst_chain: u16) -> Result<H256> {
        let stargate = crate::bridges::stargate::StargateConnector::new(self.providers[0].clone());
        stargate.bridge_tokens(&self.wallet, dst_chain, amount, amount * 95 / 100).await
    }

    async fn execute_l2_arbitrage(&self, chain: u16, amount: U256, min_profit: U256) -> Result<H256> {
        let uniswap = crate::exchanges::uniswap::UniswapConnector::new("https://arb1.arbitrum.io/rpc").await?;
        let usdc: Address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48".parse()?;
        let weth: Address = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1".parse()?;
        
        uniswap.execute_swap(&self.wallet, usdc, weth, amount, min_profit).await
    }
}

pub struct GasOracle;

impl GasOracle {
    pub fn new() -> Self { Self }
    
    pub async fn get_fast_gas_price(&self) -> Result<U256> {
        let client = reqwest::Client::new();
        let resp: serde_json::Value = client
            .get("https://api.etherscan.io/api?module=gastracker&action=gasoracle")
            .send().await?.json().await?;
        
        let gas_price = resp["result"]["FastGasPrice"].as_str().unwrap();
        Ok(U256::from(gas_price.parse::<u64>()?) * U256::exp10(9))
    }
}
