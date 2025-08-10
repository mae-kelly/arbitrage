use anyhow::Result;
use ethers::prelude::*;

pub struct UniswapConnector {
    provider: Arc<Provider<Http>>,
    router: Address,
    quoter: Address,
}

impl UniswapConnector {
    pub async fn new(rpc_url: &str) -> Result<Self> {
        let provider = Provider::<Http>::try_from(rpc_url)?;
        Ok(Self {
            provider: Arc::new(provider),
            router: "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45".parse()?,
            quoter: "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6".parse()?,
        })
    }

    pub async fn get_quote(&self, token_in: Address, token_out: Address, amount: U256) -> Result<U256> {
        let quoter_abi = r#"[{"inputs":[{"name":"tokenIn","type":"address"},{"name":"tokenOut","type":"address"},{"name":"amountIn","type":"uint256"},{"name":"fee","type":"uint24"},{"name":"sqrtPriceLimitX96","type":"uint160"}],"name":"quoteExactInputSingle","outputs":[{"name":"amountOut","type":"uint256"}],"type":"function"}]"#;
        let contract = Contract::new(self.quoter, serde_json::from_str(quoter_abi)?, self.provider.clone());
        
        let result: U256 = contract
            .method("quoteExactInputSingle", (token_in, token_out, amount, 3000u32, U256::zero()))?
            .call().await?;
        Ok(result)
    }

    pub async fn execute_swap(&self, wallet: &LocalWallet, token_in: Address, token_out: Address, amount: U256, min_out: U256) -> Result<H256> {
        let client = SignerMiddleware::new(self.provider.clone(), wallet.clone());
        let router_abi = r#"[{"inputs":[{"components":[{"name":"tokenIn","type":"address"},{"name":"tokenOut","type":"address"},{"name":"fee","type":"uint24"},{"name":"recipient","type":"address"},{"name":"deadline","type":"uint256"},{"name":"amountIn","type":"uint256"},{"name":"amountOutMinimum","type":"uint256"},{"name":"sqrtPriceLimitX96","type":"uint160"}],"name":"params","type":"tuple"}],"name":"exactInputSingle","outputs":[{"name":"amountOut","type":"uint256"}],"type":"function"}]"#;
        let contract = Contract::new(self.router, serde_json::from_str(router_abi)?, Arc::new(client));

        let deadline = chrono::Utc::now().timestamp() as u64 + 300;
        let params = (token_in, token_out, 3000u32, wallet.address(), deadline, amount, min_out, U256::zero());
        
        let tx = contract.method("exactInputSingle", (params,))?.send().await?;
        Ok(tx.tx_hash())
    }
}
