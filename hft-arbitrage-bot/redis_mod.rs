use redis::{AsyncCommands, Client, Connection};
use anyhow::Result;
use serde::{Serialize, Deserialize};
use std::time::Duration;

#[derive(Debug, Clone)]
pub struct RedisCache {
    client: Client,
}

impl RedisCache {
    pub async fn new(redis_url: &str) -> Result<Self> {
        let client = Client::open(redis_url)?;
        Ok(Self { client })
    }
    
    pub async fn get_connection(&self) -> Result<redis::aio::Connection> {
        Ok(self.client.get_async_connection().await?)
    }
    
    pub async fn cache_price(&self, key: &str, data: &crate::real_time::live_data_fetcher::LiveMarketData, ttl_seconds: u64) -> Result<()> {
        let mut conn = self.get_connection().await?;
        let serialized = serde_json::to_string(data)?;
        conn.set_ex(key, serialized, ttl_seconds).await?;
        Ok(())
    }
    
    pub async fn get_cached_price(&self, key: &str) -> Result<Option<crate::real_time::live_data_fetcher::LiveMarketData>> {
        let mut conn = self.get_connection().await?;
        let result: Option<String> = conn.get(key).await?;
        
        match result {
            Some(data) => {
                let parsed = serde_json::from_str(&data)?;
                Ok(Some(parsed))
            }
            None => Ok(None)
        }
    }
    
    pub async fn cache_opportunity(&self, key: &str, data: &crate::real_time::live_data_fetcher::ArbitrageOpportunity, ttl_seconds: u64) -> Result<()> {
        let mut conn = self.get_connection().await?;
        let serialized = serde_json::to_string(data)?;
        conn.set_ex(key, serialized, ttl_seconds).await?;
        Ok(())
    }
    
    pub async fn get_cached_opportunities(&self, pattern: &str) -> Result<Vec<crate::real_time::live_data_fetcher::ArbitrageOpportunity>> {
        let mut conn = self.get_connection().await?;
        let keys: Vec<String> = conn.keys(pattern).await?;
        let mut opportunities = Vec::new();
        
        for key in keys {
            if let Ok(Some(data)) = self.get_cached_opportunity(&key).await {
                opportunities.push(data);
            }
        }
        
        Ok(opportunities)
    }
    
    async fn get_cached_opportunity(&self, key: &str) -> Result<Option<crate::real_time::live_data_fetcher::ArbitrageOpportunity>> {
        let mut conn = self.get_connection().await?;
        let result: Option<String> = conn.get(key).await?;
        
        match result {
            Some(data) => {
                let parsed = serde_json::from_str(&data)?;
                Ok(Some(parsed))
            }
            None => Ok(None)
        }
    }
    
    pub async fn increment_counter(&self, key: &str) -> Result<i64> {
        let mut conn = self.get_connection().await?;
        Ok(conn.incr(key, 1).await?)
    }
    
    pub async fn set_rate_limit(&self, key: &str, limit: i32, window_seconds: u64) -> Result<bool> {
        let mut conn = self.get_connection().await?;
        let current: Option<i32> = conn.get(key).await?;
        
        match current {
            Some(count) if count >= limit => Ok(false),
            Some(_) => {
                conn.incr(key, 1).await?;
                Ok(true)
            }
            None => {
                conn.set_ex(key, 1, window_seconds).await?;
                Ok(true)
            }
        }
    }
}
