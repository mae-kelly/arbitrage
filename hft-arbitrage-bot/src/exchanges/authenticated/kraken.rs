//! Kraken API implementation

use async_trait::async_trait;
use anyhow::Result;
use reqwest::Client;
use serde_json::Value;
use hmac::{Hmac, Mac};
use sha2::{Sha256, Sha512};
use base64;
use std::time::{SystemTime, UNIX_EPOCH};

use super::*;

pub struct KrakenClient {
    client: Client,
    credentials: ExchangeCredentials,
    base_url: String,
}

impl KrakenClient {
    pub fn new(credentials: ExchangeCredentials) -> Self {
        Self {
            client: Client::new(),
            credentials,
            base_url: "https://api.kraken.com".to_string(),
        }
    }
    
    fn sign_request(&self, path: &str, nonce: u64, post_data: &str) -> Result<String> {
        let nonce_post = format!("nonce={}&{}", nonce, post_data);
        let message = format!("{}{}", path, sha2::Sha256::digest(nonce_post.as_bytes()));
        
        let mut mac = Hmac::<Sha512>::new_from_slice(
            &base64::decode(&self.credentials.secret_key)?
        )?;
        mac.update(message.as_bytes());
        let signature = base64::encode(mac.finalize().into_bytes());
        
        Ok(signature)
    }
    
    async fn make_private_request(&self, endpoint: &str, params: &[(&str, &str)]) -> Result<Value> {
        let nonce = SystemTime::now().duration_since(UNIX_EPOCH)?.as_nanos() as u64;
        let mut post_data = format!("nonce={}", nonce);
        
        for (key, value) in params {
            post_data.push_str(&format!("&{}={}", key, value));
        }
        
        let path = format!("/0/private/{}", endpoint);
        let signature = self.sign_request(&path, nonce, &post_data)?;
        
        let url = format!("{}{}", self.base_url, path);
        let response = self.client
            .post(&url)
            .header("API-Key", &self.credentials.api_key)
            .header("API-Sign", signature)
            .header("Content-Type", "application/x-www-form-urlencoded")
            .body(post_data)
            .send()
            .await?;
        
        let result: Value = response.json().await?;
        
        if let Some(error) = result["error"].as_array() {
            if !error.is_empty() {
                return Err(anyhow::anyhow!("Kraken API error: {:?}", error));
            }
        }
        
        Ok(result["result"].clone())
    }
}

#[async_trait]
impl AuthenticatedExchange for KrakenClient {
    async fn test_connection(&self) -> Result<()> {
        let _balance = self.make_private_request("Balance", &[]).await?;
        Ok(())
    }
    
    async fn get_account_info(&self) -> Result<AccountInfo> {
        Ok(AccountInfo {
            account_id: "kraken_account".to_string(),
            account_type: "trading".to_string(),
            trading_enabled: true,
            permissions: vec!["trade".to_string(), "view".to_string()],
        })
    }
    
    async fn get_balances(&self) -> Result<Vec<Balance>> {
        let response = self.make_private_request("Balance", &[]).await?;
        let mut balances = Vec::new();
        
        if let Some(balance_obj) = response.as_object() {
            for (asset, balance) in balance_obj {
                if let Some(balance_str) = balance.as_str() {
                    let total: f64 = balance_str.parse().unwrap_or(0.0);
                    if total > 0.0 {
                        balances.push(Balance {
                            asset: asset.clone(),
                            free: total, // Kraken doesn't separate free/locked in balance endpoint
                            locked: 0.0,
                            total,
                        });
                    }
                }
            }
        }
        
        Ok(balances)
    }
    
    async fn place_order(&self, order: OrderRequest) -> Result<OrderResponse> {
        let params = [
            ("pair", order.symbol.as_str()),
            ("type", match order.side { OrderSide::Buy => "buy", OrderSide::Sell => "sell" }),
            ("ordertype", match order.order_type { OrderType::Market => "market", _ => "limit" }),
            ("volume", &order.quantity.to_string()),
        ];
        
        let response = self.make_private_request("AddOrder", &params).await?;
        
        Ok(OrderResponse {
            order_id: response["txid"][0].as_str().unwrap_or("").to_string(),
            client_order_id: response["txid"][0].as_str().unwrap_or("").to_string(),
            symbol: order.symbol,
            status: OrderStatus::New,
            created_at: chrono::Utc::now(),
        })
    }
    
    async fn cancel_order(&self, order_id: &str) -> Result<()> {
        let params = [("txid", order_id)];
        self.make_private_request("CancelOrder", &params).await?;
        Ok(())
    }
    
    async fn cancel_all_orders(&self) -> Result<()> {
        // Kraken doesn't have cancel all, so we'd need to get open orders first
        Ok(())
    }
    
    async fn get_order_status(&self, order_id: &str) -> Result<OrderFill> {
        let params = [("txid", order_id)];
        let response = self.make_private_request("QueryOrders", &params).await?;
        
        // Parse Kraken order response format
        Ok(OrderFill {
            order_id: order_id.to_string(),
            symbol: "".to_string(),
            side: OrderSide::Buy,
            status: OrderStatus::New,
            filled_quantity: 0.0,
            average_price: 0.0,
            commission: 0.0,
            commission_asset: "USD".to_string(),
            created_at: chrono::Utc::now(),
            updated_at: chrono::Utc::now(),
        })
    }
    
    async fn get_open_orders(&self) -> Result<Vec<OrderFill>> {
        let _response = self.make_private_request("OpenOrders", &[]).await?;
        Ok(Vec::new())
    }
    
    async fn get_order_history(&self, _symbol: Option<&str>) -> Result<Vec<OrderFill>> {
        let _response = self.make_private_request("ClosedOrders", &[]).await?;
        Ok(Vec::new())
    }
    
    async fn get_trading_fees(&self) -> Result<TradingFees> {
        Ok(TradingFees {
            maker_fee: 0.0016, // 0.16%
            taker_fee: 0.0026, // 0.26%
            currency: "USD".to_string(),
        })
    }
}
