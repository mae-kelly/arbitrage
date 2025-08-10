use anyhow::Result;
use reqwest;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PoolData {
    pub id: String,
    pub token0: TokenInfo,
    pub token1: TokenInfo,
    pub reserve0: String,
    pub reserve1: String,
    pub total_value_locked: String,
    pub volume_24h: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenInfo {
    pub id: String,
    pub symbol: String,
    pub decimals: u8,
}

pub struct GraphIndexer {
    endpoints: HashMap<String, String>,
    cache: Arc<RwLock<HashMap<String, Vec<PoolData>>>>,
    client: reqwest::Client,
}

impl GraphIndexer {
    pub async fn new() -> Result<Self> {
        let mut endpoints = HashMap::new();
        endpoints.insert(
            "uniswap_v3".to_string(),
            "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3".to_string(),
        );
        endpoints.insert(
            "sushiswap".to_string(),
            "https://api.thegraph.com/subgraphs/name/sushiswap/exchange".to_string(),
        );
        endpoints.insert(
            "quickswap".to_string(),
            "https://api.thegraph.com/subgraphs/name/sameepsi/quickswap-v3".to_string(),
        );
        
        Ok(Self {
            endpoints,
            cache: Arc::new(RwLock::new(HashMap::new())),
            client: reqwest::Client::new(),
        })
    }
    
    pub async fn query_pools(&self, protocol: &str) -> Result<Vec<PoolData>> {
        let endpoint = self.endpoints.get(protocol)
            .ok_or_else(|| anyhow::anyhow!("Unknown protocol"))?;
        
        let query = r#"
        {
            pools(first: 100, orderBy: totalValueLockedUSD, orderDirection: desc) {
                id
                token0 {
                    id
                    symbol
                    decimals
                }
                token1 {
                    id
                    symbol
                    decimals
                }
                totalValueLockedToken0
                totalValueLockedToken1
                totalValueLockedUSD
                volumeUSD
            }
        }
        "#;
        
        let response = self.client
            .post(endpoint)
            .json(&serde_json::json!({ "query": query }))
            .send()
            .await?;
        
        let json: serde_json::Value = response.json().await?;
        
        let pools = self.parse_pools(json)?;
        
        let mut cache = self.cache.write().await;
        cache.insert(protocol.to_string(), pools.clone());
        
        Ok(pools)
    }
    
    fn parse_pools(&self, json: serde_json::Value) -> Result<Vec<PoolData>> {
        let pools_json = json["data"]["pools"]
            .as_array()
            .ok_or_else(|| anyhow::anyhow!("Invalid response format"))?;
        
        let mut pools = Vec::new();
        
        for pool_json in pools_json {
            let pool = PoolData {
                id: pool_json["id"].as_str().unwrap_or("").to_string(),
                token0: TokenInfo {
                    id: pool_json["token0"]["id"].as_str().unwrap_or("").to_string(),
                    symbol: pool_json["token0"]["symbol"].as_str().unwrap_or("").to_string(),
                    decimals: pool_json["token0"]["decimals"].as_u64().unwrap_or(18) as u8,
                },
                token1: TokenInfo {
                    id: pool_json["token1"]["id"].as_str().unwrap_or("").to_string(),
                    symbol: pool_json["token1"]["symbol"].as_str().unwrap_or("").to_string(),
                    decimals: pool_json["token1"]["decimals"].as_u64().unwrap_or(18) as u8,
                },
                reserve0: pool_json["totalValueLockedToken0"].as_str().unwrap_or("0").to_string(),
                reserve1: pool_json["totalValueLockedToken1"].as_str().unwrap_or("0").to_string(),
                total_value_locked: pool_json["totalValueLockedUSD"].as_str().unwrap_or("0").to_string(),
                volume_24h: pool_json["volumeUSD"].as_str().unwrap_or("0").to_string(),
            };
            pools.push(pool);
        }
        
        Ok(pools)
    }
    
    pub async fn find_arbitrage_opportunities(&self) -> Result<Vec<(String, String, f64)>> {
        let mut opportunities = Vec::new();
        
        for (protocol_a, _) in &self.endpoints {
            for (protocol_b, _) in &self.endpoints {
                if protocol_a != protocol_b {
                    let pools_a = self.query_pools(protocol_a).await?;
                    let pools_b = self.query_pools(protocol_b).await?;
                    
                    for pool_a in &pools_a {
                        for pool_b in &pools_b {
                            if pool_a.token0.symbol == pool_b.token0.symbol 
                                && pool_a.token1.symbol == pool_b.token1.symbol {
                                
                                let price_a = pool_a.reserve1.parse::<f64>().unwrap_or(0.0) 
                                    / pool_a.reserve0.parse::<f64>().unwrap_or(1.0);
                                let price_b = pool_b.reserve1.parse::<f64>().unwrap_or(0.0) 
                                    / pool_b.reserve0.parse::<f64>().unwrap_or(1.0);
                                
                                let spread = (price_a - price_b).abs() / price_a;
                                
                                if spread > 0.002 {
                                    opportunities.push((
                                        format!("{}-{}", protocol_a, pool_a.id),
                                        format!("{}-{}", protocol_b, pool_b.id),
                                        spread,
                                    ));
                                }
                            }
                        }
                    }
                }
            }
        }
        
        Ok(opportunities)
    }
}
