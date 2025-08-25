use ethers::prelude::*;
use std::sync::Arc;


use crate::arbitrage::Opportunity;
use crate::Config;

pub struct FlashLoanManager {
    client: Arc<SignerMiddleware<Provider<Http>, LocalWallet>>,
    config: Arc<Config>,
    aave_pool: Address,
    balancer_vault: Address,
    uniswap_v3_factory: Address,
}

impl FlashLoanManager {
    pub fn new(client: Arc<SignerMiddleware<Provider<Http>, LocalWallet>>, config: Arc<Config>) -> Self {
        Self {
            client,
            config,
            aave_pool: "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2".parse().unwrap(),
            balancer_vault: "0xBA12222222228d8Ba445958a75a0704d566BF2C8".parse().unwrap(),
            uniswap_v3_factory: "0x1F98431c8aD98523631AE4a59f267346ea31F984".parse().unwrap(),
        }
    }
    
    pub async fn execute_arbitrage(&self, opportunity: dashmap::mapref::one::Ref<'_, String, Opportunity>) -> anyhow::Result<()> {
        if self.config.mode == "test" {
            return self.simulate_arbitrage(&opportunity).await;
        }
        
        let flash_loan_amount = opportunity.amount_in;
        let flash_loan_provider = self.select_provider(&opportunity).await?;
        
        match flash_loan_provider.as_str() {
            "aave" if self.config.use_aave => self.execute_aave_flash_loan(&opportunity, flash_loan_amount).await,
            "balancer" if self.config.use_balancer => self.execute_balancer_flash_loan(&opportunity, flash_loan_amount).await,
            "uniswap" if self.config.use_uniswap => self.execute_uniswap_flash_loan(&opportunity, flash_loan_amount).await,
            _ => self.execute_standard_arbitrage(&opportunity).await,
        }
    }
    
    async fn simulate_arbitrage(&self, opportunity: &dashmap::mapref::one::Ref<'_, String, Opportunity>) -> anyhow::Result<()> {
        let gas_estimate = U256::from(350000);
        let gas_price = self.client.get_gas_price().await?;
        let gas_cost = gas_estimate * gas_price;
        
        let simulated_profit = opportunity.profit_wei.saturating_sub(gas_cost);
        
        println!("SIMULATION: {} -> {} via {}/{}", 
            opportunity.token_in, 
            opportunity.token_out,
            opportunity.dex_buy,
            opportunity.dex_sell
        );
        println!("Expected Profit: {} ETH", ethers::utils::format_ether(simulated_profit));
        
        Ok(())
    }
    
    async fn select_provider(&self, _opportunity: &dashmap::mapref::one::Ref<'_, String, Opportunity>) -> anyhow::Result<String> {
        let providers = vec![
            ("aave", self.config.use_aave, 0.0009),
            ("balancer", self.config.use_balancer, 0.0),
            ("uniswap", self.config.use_uniswap, 0.0005),
        ];
        
        let best_provider = providers
            .into_iter()
            .filter(|(_, enabled, _)| *enabled)
            .min_by(|a, b| a.2.partial_cmp(&b.2).unwrap())
            .map(|(name, _, _)| name.to_string())
            .unwrap_or_else(|| "aave".to_string());
        
        Ok(best_provider)
    }
    
    async fn execute_aave_flash_loan(&self, opportunity: &dashmap::mapref::one::Ref<'_, String, Opportunity>, amount: U256) -> anyhow::Result<()> {
        let flash_loan_abi = ethers::abi::Function {
            name: "flashLoanSimple".to_string(),
            inputs: vec![
                ethers::abi::Param { name: "receiverAddress".to_string(), kind: ethers::abi::ParamType::Address, internal_type: None },
                ethers::abi::Param { name: "asset".to_string(), kind: ethers::abi::ParamType::Address, internal_type: None },
                ethers::abi::Param { name: "amount".to_string(), kind: ethers::abi::ParamType::Uint(256), internal_type: None },
                ethers::abi::Param { name: "params".to_string(), kind: ethers::abi::ParamType::Bytes, internal_type: None },
                ethers::abi::Param { name: "referralCode".to_string(), kind: ethers::abi::ParamType::Uint(16), internal_type: None },
            ],
            outputs: vec![],
            constant: None,
            state_mutability: ethers::abi::StateMutability::NonPayable,
        };
        
        let params = ethers::abi::encode(&[
            ethers::abi::Token::Address(opportunity.token_out.into()),
            ethers::abi::Token::Uint(opportunity.amount_out.into()),
            ethers::abi::Token::String(opportunity.dex_buy.clone()),
            ethers::abi::Token::String(opportunity.dex_sell.clone()),
        ]);
        
        let calldata = flash_loan_abi.encode_input(&[
            ethers::abi::Token::Address(self.config.wallet_address.parse::<Address>()?.into()),
            ethers::abi::Token::Address(opportunity.token_in.into()),
            ethers::abi::Token::Uint(amount.into()),
            ethers::abi::Token::Bytes(params),
            ethers::abi::Token::Uint(0.into()),
        ])?;
        
        let tx = TransactionRequest::new()
            .to(self.aave_pool)
            .data(calldata)
            .gas(U256::from(500000))
            .gas_price(opportunity.gas_price);
        
        let pending_tx = self.client.send_transaction(tx, None).await?;
        let receipt = pending_tx.await?;
        
        println!("Flash loan executed: {:?}", receipt);
        Ok(())
    }
    
    async fn execute_balancer_flash_loan(&self, opportunity: &dashmap::mapref::one::Ref<'_, String, Opportunity>, amount: U256) -> anyhow::Result<()> {
        let flash_loan_abi = ethers::abi::Function {
            name: "flashLoan".to_string(),
            inputs: vec![
                ethers::abi::Param { name: "recipient".to_string(), kind: ethers::abi::ParamType::Address, internal_type: None },
                ethers::abi::Param { name: "tokens".to_string(), kind: ethers::abi::ParamType::Array(Box::new(ethers::abi::ParamType::Address)), internal_type: None },
                ethers::abi::Param { name: "amounts".to_string(), kind: ethers::abi::ParamType::Array(Box::new(ethers::abi::ParamType::Uint(256))), internal_type: None },
                ethers::abi::Param { name: "userData".to_string(), kind: ethers::abi::ParamType::Bytes, internal_type: None },
            ],
            outputs: vec![],
            constant: None,
            state_mutability: ethers::abi::StateMutability::NonPayable,
        };
        
        let user_data = ethers::abi::encode(&[
            ethers::abi::Token::Address(opportunity.token_out.into()),
            ethers::abi::Token::String(opportunity.dex_buy.clone()),
            ethers::abi::Token::String(opportunity.dex_sell.clone()),
        ]);
        
        let calldata = flash_loan_abi.encode_input(&[
            ethers::abi::Token::Address(self.config.wallet_address.parse::<Address>()?.into()),
            ethers::abi::Token::Array(vec![ethers::abi::Token::Address(opportunity.token_in.into())]),
            ethers::abi::Token::Array(vec![ethers::abi::Token::Uint(amount.into())]),
            ethers::abi::Token::Bytes(user_data),
        ])?;
        
        let tx = TransactionRequest::new()
            .to(self.balancer_vault)
            .data(calldata)
            .gas(U256::from(600000))
            .gas_price(opportunity.gas_price);
        
        let pending_tx = self.client.send_transaction(tx, None).await?;
        let receipt = pending_tx.await?;
        
        println!("Balancer flash loan executed: {:?}", receipt);
        Ok(())
    }
    
    async fn execute_uniswap_flash_loan(&self, opportunity: &dashmap::mapref::one::Ref<'_, String, Opportunity>, amount: U256) -> anyhow::Result<()> {
        let pool_address = self.get_uniswap_v3_pool(opportunity.token_in, opportunity.token_out).await?;
        
        let flash_abi = ethers::abi::Function {
            name: "flash".to_string(),
            inputs: vec![
                ethers::abi::Param { name: "recipient".to_string(), kind: ethers::abi::ParamType::Address, internal_type: None },
                ethers::abi::Param { name: "amount0".to_string(), kind: ethers::abi::ParamType::Uint(256), internal_type: None },
                ethers::abi::Param { name: "amount1".to_string(), kind: ethers::abi::ParamType::Uint(256), internal_type: None },
                ethers::abi::Param { name: "data".to_string(), kind: ethers::abi::ParamType::Bytes, internal_type: None },
            ],
            outputs: vec![],
            constant: None,
            state_mutability: ethers::abi::StateMutability::NonPayable,
        };
        
        let callback_data = ethers::abi::encode(&[
            ethers::abi::Token::Address(opportunity.token_out.into()),
            ethers::abi::Token::String(opportunity.dex_buy.clone()),
            ethers::abi::Token::String(opportunity.dex_sell.clone()),
        ]);
        
        let (amount0, amount1) = if opportunity.token_in < opportunity.token_out {
            (amount, U256::zero())
        } else {
            (U256::zero(), amount)
        };
        
        let calldata = flash_abi.encode_input(&[
            ethers::abi::Token::Address(self.config.wallet_address.parse::<Address>()?.into()),
            ethers::abi::Token::Uint(amount0.into()),
            ethers::abi::Token::Uint(amount1.into()),
            ethers::abi::Token::Bytes(callback_data),
        ])?;
        
        let tx = TransactionRequest::new()
            .to(pool_address)
            .data(calldata)
            .gas(U256::from(700000))
            .gas_price(opportunity.gas_price);
        
        let pending_tx = self.client.send_transaction(tx, None).await?;
        let receipt = pending_tx.await?;
        
        println!("Uniswap V3 flash loan executed: {:?}", receipt);
        Ok(())
    }
    
    async fn get_uniswap_v3_pool(&self, token0: Address, token1: Address) -> anyhow::Result<Address> {
        let (token0, token1) = if token0 < token1 { (token0, token1) } else { (token1, token0) };
        let fee = 3000u32;
        
        let get_pool_abi = ethers::abi::Function {
            name: "getPool".to_string(),
            inputs: vec![
                ethers::abi::Param { name: "tokenA".to_string(), kind: ethers::abi::ParamType::Address, internal_type: None },
                ethers::abi::Param { name: "tokenB".to_string(), kind: ethers::abi::ParamType::Address, internal_type: None },
                ethers::abi::Param { name: "fee".to_string(), kind: ethers::abi::ParamType::Uint(24), internal_type: None },
            ],
            outputs: vec![
                ethers::abi::Param { name: "pool".to_string(), kind: ethers::abi::ParamType::Address, internal_type: None },
            ],
            constant: None,
            state_mutability: ethers::abi::StateMutability::View,
        };
        
        let calldata = get_pool_abi.encode_input(&[
            ethers::abi::Token::Address(token0.into()),
            ethers::abi::Token::Address(token1.into()),
            ethers::abi::Token::Uint(fee.into()),
        ])?;
        
        let tx = TransactionRequest::new()
            .to(self.uniswap_v3_factory)
            .data(calldata);
        
        let result = self.client.call(&tx.into(), None).await?;
        let pool_address = Address::from_slice(&result[12..32]);
        
        Ok(pool_address)
    }
    
    async fn execute_standard_arbitrage(&self, _opportunity: &dashmap::mapref::one::Ref<'_, String, Opportunity>) -> anyhow::Result<()> {
        println!("Executing standard arbitrage without flash loan");
        Ok(())
    }
}