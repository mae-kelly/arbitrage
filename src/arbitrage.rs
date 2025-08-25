use ethers::prelude::*;
use std::sync::Arc;
use rust_decimal::prelude::*;
use dashmap::DashMap;

use serde::{Serialize, Deserialize};


use crate::ml_predictor::MLPredictor;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Opportunity {
    pub token_in: Address,
    pub token_out: Address,
    pub amount_in: U256,
    pub amount_out: U256,
    pub dex_buy: String,
    pub dex_sell: String,
    pub gas_price: U256,
    pub block_number: u64,
    pub timestamp: u64,
    pub profit_wei: U256,
    pub confidence: f64,
}

pub struct ArbitrageEngine {
    client: Arc<SignerMiddleware<Provider<Http>, LocalWallet>>,
    ml_predictor: Arc<MLPredictor>,
    price_cache: Arc<DashMap<(Address, Address), U256>>,
    dex_routers: Arc<DashMap<String, Address>>,
}

impl ArbitrageEngine {
    pub fn new(client: Arc<SignerMiddleware<Provider<Http>, LocalWallet>>, ml_predictor: Arc<MLPredictor>) -> Self {
        let dex_routers = Arc::new(DashMap::new());
        dex_routers.insert("uniswap_v2".to_string(), "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D".parse().unwrap());
        dex_routers.insert("sushiswap".to_string(), "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F".parse().unwrap());
        dex_routers.insert("uniswap_v3".to_string(), "0xE592427A0AEce92De3Edee1F18E0157C05861564".parse().unwrap());
        dex_routers.insert("balancer".to_string(), "0xBA12222222228d8Ba445958a75a0704d566BF2C8".parse().unwrap());
        dex_routers.insert("curve".to_string(), "0x99a58482BD75cbab83b27EC03CA68fF489b5788f".parse().unwrap());
        
        Self {
            client,
            ml_predictor,
            price_cache: Arc::new(DashMap::new()),
            dex_routers,
        }
    }
    
    pub async fn calculate_profit(&self, opp: &dashmap::mapref::one::Ref<'_, String, Opportunity>) -> anyhow::Result<f64> {
        let buy_price = self.get_price(opp.token_in, opp.token_out, &opp.dex_buy).await?;
        let sell_price = self.get_price(opp.token_out, opp.token_in, &opp.dex_sell).await?;
        
        let amount_in_dec = Decimal::from_str(&opp.amount_in.to_string())?;
        let buy_price_dec = Decimal::from_str(&buy_price.to_string())?;
        let sell_price_dec = Decimal::from_str(&sell_price.to_string())?;
        
        let tokens_bought = amount_in_dec * buy_price_dec / Decimal::from(10u64.pow(18));
        let proceeds = tokens_bought * sell_price_dec / Decimal::from(10u64.pow(18));
        let gross_profit = proceeds - amount_in_dec;
        
        let gas_cost = Decimal::from_str(&opp.gas_price.to_string())? * Decimal::from(350000);
        let net_profit = gross_profit - gas_cost;
        
        let ml_adjustment = self.ml_predictor.get_confidence_multiplier(opp.value()).await;
        let adjusted_profit = net_profit * Decimal::from_f64(ml_adjustment).unwrap_or(Decimal::ONE);
        
        Ok(adjusted_profit.to_f64().unwrap_or(0.0) / 1e18)
    }
    
    async fn get_price(&self, token_in: Address, token_out: Address, dex: &str) -> anyhow::Result<U256> {
        let cache_key = (token_in, token_out);
        if let Some(cached) = self.price_cache.get(&cache_key) {
            return Ok(*cached);
        }
        
        let router = self.dex_routers.get(dex).map(|r| *r).unwrap_or_default();
        let price = self.fetch_onchain_price(router, token_in, token_out).await?;
        self.price_cache.insert(cache_key, price);
        
        Ok(price)
    }
    
    async fn fetch_onchain_price(&self, router: Address, token_in: Address, token_out: Address) -> anyhow::Result<U256> {
        let amount_in = U256::from(10).pow(U256::from(18));
        
        let _get_amounts_out = "getAmountsOut(uint256,address[])(uint256[])";
        let path = vec![token_in, token_out];
        
        let tx = TransactionRequest::new()
            .to(router)
            .data(ethers::abi::encode(&[
                ethers::abi::Token::Uint(amount_in.into()),
                ethers::abi::Token::Array(path.iter().map(|a| ethers::abi::Token::Address(a.0.into())).collect()),
            ]));
        
        let result = self.client.call(&tx.into(), None).await?;
        let amounts: Vec<U256> = ethers::abi::decode(&[ethers::abi::ParamType::Array(Box::new(ethers::abi::ParamType::Uint(256)))], &result)?
            .into_iter()
            .next()
            .and_then(|t| t.into_array())
            .unwrap_or_default()
            .into_iter()
            .filter_map(|t| t.into_uint().map(|u| U256::from(u.as_u128())))
            .collect();
        
        Ok(amounts.get(1).copied().unwrap_or_default())
    }
    
    pub async fn find_opportunities(&self) -> Vec<Opportunity> {
        let tokens = self.get_top_tokens().await;
        let dexes = vec!["uniswap_v2", "sushiswap", "uniswap_v3", "balancer", "curve"];
        
        let opportunities: Vec<Opportunity> = tokens.iter()
            .flat_map(|token_a| {
                tokens.iter()
                    .filter(|token_b| token_a != *token_b)
                    .flat_map(|token_b| {
                        dexes.iter()
                            .flat_map(|dex_buy| {
                                dexes.iter()
                                    .filter(|dex_sell| dex_buy != *dex_sell)
                                    .filter_map(|dex_sell| {
                                        self.create_opportunity(*token_a, *token_b, dex_buy, dex_sell)
                                    })
                                    .collect::<Vec<_>>()
                            })
                            .collect::<Vec<_>>()
                    })
                    .collect::<Vec<_>>()
            })
            .collect();
        
        opportunities
    }
    
    async fn get_top_tokens(&self) -> Vec<Address> {
        vec![
            "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2".parse().unwrap(),
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48".parse().unwrap(),
            "0xdAC17F958D2ee523a2206206994597C13D831ec7".parse().unwrap(),
            "0x6B175474E89094C44Da98b954EedeAC495271d0F".parse().unwrap(),
            "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599".parse().unwrap(),
            "0x514910771AF9Ca656af840dff83E8264EcF986CA".parse().unwrap(),
            "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984".parse().unwrap(),
            "0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0".parse().unwrap(),
        ]
    }
    
    fn create_opportunity(&self, token_in: Address, token_out: Address, dex_buy: &str, dex_sell: &str) -> Option<Opportunity> {
        Some(Opportunity {
            token_in,
            token_out,
            amount_in: U256::from(10).pow(U256::from(18)),
            amount_out: U256::zero(),
            dex_buy: dex_buy.to_string(),
            dex_sell: dex_sell.to_string(),
            gas_price: U256::from(30) * U256::from(10).pow(U256::from(9)),
            block_number: 0,
            timestamp: chrono::Utc::now().timestamp() as u64,
            profit_wei: U256::zero(),
            confidence: 0.5,
        })
    }
}