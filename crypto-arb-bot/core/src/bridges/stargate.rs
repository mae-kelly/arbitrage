use anyhow::Result;
use ethers::prelude::*;

pub struct StargateConnector {
    router: Address,
    provider: Arc<Provider<Http>>,
}

impl StargateConnector {
    pub fn new(provider: Arc<Provider<Http>>) -> Self {
        Self {
            router: "0x8731d54E9D02c286767d56ac03e8037C07e01e98".parse().unwrap(),
            provider,
        }
    }

    pub async fn get_bridge_fee(&self, dst_chain: u16, src_pool: u256, dst_pool: u256, amount: U256) -> Result<U256> {
        let abi = r#"[{"inputs":[{"name":"_dstChainId","type":"uint16"},{"name":"_srcPoolId","type":"uint256"},{"name":"_dstPoolId","type":"uint256"},{"name":"_amountLD","type":"uint256"}],"name":"quoteLayerZeroFee","outputs":[{"name":"","type":"uint256"},{"name":"","type":"uint256"}],"type":"function"}]"#;
        let contract = Contract::new(self.router, serde_json::from_str(abi)?, self.provider.clone());
        
        let (fee, _): (U256, U256) = contract
            .method("quoteLayerZeroFee", (dst_chain, src_pool, dst_pool, amount))?
            .call().await?;
        Ok(fee)
    }

    pub async fn bridge_tokens(&self, wallet: &LocalWallet, dst_chain: u16, amount: U256, min_amount: U256) -> Result<H256> {
        let client = SignerMiddleware::new(self.provider.clone(), wallet.clone());
        let abi = r#"[{"inputs":[{"name":"_dstChainId","type":"uint16"},{"name":"_srcPoolId","type":"uint256"},{"name":"_dstPoolId","type":"uint256"},{"name":"_refundAddress","type":"address"},{"name":"_amountLD","type":"uint256"},{"name":"_minAmountLD","type":"uint256"},{"name":"_lzTxParams","type":"tuple"},{"name":"_to","type":"bytes"},{"name":"_payload","type":"bytes"}],"name":"swap","type":"function"}]"#;
        let contract = Contract::new(self.router, serde_json::from_str(abi)?, Arc::new(client));

        let lz_params = (500000u256, U256::zero(), "0x".as_bytes());
        let to_bytes = wallet.address().as_bytes();
        
        let tx = contract
            .method("swap", (dst_chain, 1u256, 1u256, wallet.address(), amount, min_amount, lz_params, to_bytes, "0x".as_bytes()))?
            .send().await?;
        Ok(tx.tx_hash())
    }
}
