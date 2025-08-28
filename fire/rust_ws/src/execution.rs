// core/rust_ws/src/execution.rs
use ethers::prelude::*;
use ethers::core::k256::ecdsa::SigningKey;
use std::sync::Arc;
use std::convert::TryFrom;

pub struct ExecutionEngine {
    wallet: LocalWallet,
    provider: Arc<Provider<Ws>>,
    flash_loan_contract: Address,
    nonce: U256,
}

impl ExecutionEngine {
    pub async fn new(private_key: &str, provider_url: &str, flash_loan_address: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let wallet = private_key.parse::<LocalWallet>()?;
        let provider = Provider::<Ws>::connect(provider_url).await?;
        let provider = Arc::new(provider);
        let flash_loan_contract = flash_loan_address.parse()?;
        
        let wallet_address = wallet.address();
        let nonce = provider.get_transaction_count(wallet_address, None).await?;
        
        Ok(Self {
            wallet,
            provider,
            flash_loan_contract,
            nonce,
        })
    }
    
    pub async fn execute_arbitrage(
        &mut self,
        token_a: Address,
        token_b: Address,
        amount_in: U256,
        expected_profit: U256,
        gas_price: U256,
    ) -> Result<H256, Box<dyn std::error::Error>> {
        let contract_abi = ethers::abi::parse_abi(&[
            "function executeArbitrage(address tokenA, address tokenB, uint256 amountIn, uint256 expectedProfit) external",
        ])?;
        
        let contract = Contract::new(self.flash_loan_contract, contract_abi, self.provider.clone());
        
        let call = contract.method::<_, ()>("executeArbitrage", (token_a, token_b, amount_in, expected_profit))?;
        
        let tx = call
            .tx
            .set_gas_price(gas_price)
            .set_gas(500000u64)
            .set_nonce(self.nonce);
        
        let signed_tx = self.wallet.sign_transaction(&tx.into()).await?;
        let pending_tx = self.provider.send_raw_transaction(signed_tx.into()).await?;
        
        self.nonce += U256::one();
        
        Ok(pending_tx.tx_hash())
    }
    
    pub async fn send_bundle_flashbots(
        &mut self,
        transactions: Vec<TypedTransaction>,
        target_block: U64,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let flashbots_relay = "https://relay.flashbots.net";
        
        let bundle = transactions
            .into_iter()
            .map(|tx| self.wallet.sign_transaction(&tx))
            .collect::<Vec<_>>();
        
        let signed_txs = futures::future::join_all(bundle).await;
        
        let client = reqwest::Client::new();
        let response = client
            .post(flashbots_relay)
            .json(&serde_json::json!({
                "jsonrpc": "2.0",
                "method": "eth_sendBundle",
                "params": [{
                    "txs": signed_txs.iter().map(|tx| format!("0x{}", hex::encode(tx.as_ref().unwrap()))).collect::<Vec<_>>(),
                    "blockNumber": format!("0x{:x}", target_block.as_u64()),
                }],
                "id": 1,
            }))
            .send()
            .await?;
        
        Ok(())
    }
    
    pub async fn estimate_gas_price(&self) -> U256 {
        let base_fee = self.provider.get_block(BlockNumber::Latest).await.unwrap().unwrap().base_fee_per_gas.unwrap();
        let priority_fee = U256::from(2000000000u64);
        base_fee + priority_fee
    }
    
    pub async fn simulate_transaction(
        &self,
        token_a: Address,
        token_b: Address,
        amount_in: U256,
    ) -> Result<U256, Box<dyn std::error::Error>> {
        let fork_block = self.provider.get_block_number().await?;
        
        let uniswap_v2_router = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D".parse::<Address>()?;
        let uniswap_v3_router = "0xE592427A0AEce92De3Edee1F18E0157C05861564".parse::<Address>()?;
        
        let v2_abi = ethers::abi::parse_abi(&[
            "function getAmountsOut(uint amountIn, address[] memory path) public view returns (uint[] memory amounts)",
        ])?;
        
        let v3_abi = ethers::abi::parse_abi(&[
            "function quoteExactInputSingle(address tokenIn, address tokenOut, uint24 fee, uint256 amountIn, uint160 sqrtPriceLimitX96) external returns (uint256 amountOut)",
        ])?;
        
        let v2_contract = Contract::new(uniswap_v2_router, v2_abi, self.provider.clone());
        let v3_contract = Contract::new(uniswap_v3_router, v3_abi, self.provider.clone());
        
        let path = vec![token_a, token_b];
        let v2_amounts: Vec<U256> = v2_contract.method("getAmountsOut", (amount_in, path.clone()))?.call().await?;
        
        let v3_amount: U256 = v3_contract
            .method("quoteExactInputSingle", (token_a, token_b, 3000u32, amount_in, U256::zero()))?
            .call()
            .await?;
        
        let profit = if v3_amount > v2_amounts[1] {
            v3_amount - v2_amounts[1]
        } else {
            v2_amounts[1] - v3_amount
        };
        
        Ok(profit)
    }
    
    pub async fn check_profitability(
        &self,
        expected_profit: U256,
        gas_price: U256,
    ) -> bool {
        let gas_cost = gas_price * U256::from(500000u64);
        expected_profit > gas_cost * U256::from(2u64)
    }
}