//! Coinbase Advanced Trade API implementation

use async_trait::async_trait;
use anyhow::Result;
use reqwest::Client;
use serde_json::Value;
use hmac::{Hmac, Mac};
use sha2::Sha256;
use base64;
use std::time::{SystemTime, UNIX_EPOCH};

use super::*;

pub struct CoinbaseClient {
    client: Client,
    credentials: ExchangeCredentials,
    base_url: String,
}

impl CoinbaseClient {
    pub fn new(credentials: ExchangeCredentials) -> Self {
        let base_url = if credentials.sandbox {
            "https://api-public.sandbox.exchange.coinbase.com".to_string()
        } else {
            "https://api.exchange.coinbase.com".to_string()
        };
        
        Self {
            client: Client::new(),
            credentials,
            base_url,
        }
    }
    
    fn sign_request(&self, method: &str, path: &str, body: &str) -> Result<(String, String)> {
        let timestamp = SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs().to_string();
        let message = format!("{}{}{}{}", timestamp, method, path, body);
        
        let mut mac = Hmac::<Sha256>::new_from_slice(
            &base64::decode(&self.credentials.secret_key)?
        )?;
        mac.update(message.as_bytes());
        let signature = base64::encode(mac.finalize().into_bytes());
        
        Ok((timestamp, signature))
    }
    
    async fn make_request(&self, method: &str, path: &str, body: Option<Value>) -> Result<Value> {
        let body_str = body.as_ref().map(|b| b.to_string()).unwrap_or_default();
        let (timestamp, signature) = self.sign_request(method, path, &body_str)?;
        
        let url = format!("{}{}", self.base_url, path);
        let mut request = match method {
            "GET" => self.client.get(&url),
            "POST" => self.client.post(&url),
            "DELETE" => self.client.delete(&url),
            _ => return Err(anyhow::anyhow!("Unsupported method: {}", method)),
        };
        
        request = request
            .header("CB-ACCESS-KEY", &self.credentials.api_key)
            .header("CB-ACCESS-SIGN", signature)
            .header("CB-ACCESS-TIMESTAMP", timestamp)
            .header("CB-ACCESS-PASSPHRASE", self.credentials.passphrase.as_ref().unwrap_or(&String::new()))
            .header("Content-Type", "application/json");
        
        if let Some(body) = body {
            request = request.json(&body);
        }
        
        let response = request.send().await?;
        
        if !response.status().is_success() {
            let error_text = response.text().await?;
            return Err(anyhow::anyhow!("Coinbase API error: {}", error_text));
        }
        
        Ok(response.json().await?)
    }
}

#[async_trait]
impl AuthenticatedExchange for CoinbaseClient {
    async fn test_connection(&self) -> Result<()> {
        let _accounts = self.make_request("GET", "/accounts", None).await?;
        Ok(())
    }
    
    async fn get_account_info(&self) -> Result<AccountInfo> {
        let response = self.make_request("GET", "/accounts", None).await?;
        
        Ok(AccountInfo {
            account_id: "coinbase_account".to_string(),
            account_type: "trading".to_string(),
            trading_enabled: true,
            permissions: vec!["trade".to_string(), "view".to_string()],
        })
    }
    
    async fn get_balances(&self) -> Result<Vec<Balance>> {
        let response = self.make_request("GET", "/accounts", None).await?;
        let mut balances = Vec::new();
        
        if let Some(accounts) = response.as_array() {
            for account in accounts {
                if let (Some(currency), Some(balance), Some(available)) = (
                    account["currency"].as_str(),
                    account["balance"].as_str(),
                    account["available"].as_str(),
                ) {
                    let total: f64 = balance.parse().unwrap_or(0.0);
                    let free: f64 = available.parse().unwrap_or(0.0);
                    
                    if total > 0.0 {
                        balances.push(Balance {
                            asset: currency.to_string(),
                            free,
                            locked: total - free,
                            total,
                        });
                    }
                }
            }
        }
        
        Ok(balances)
    }
    
    async fn place_order(&self, order: OrderRequest) -> Result<OrderResponse> {
        let order_data = serde_json::json!({
            "type": match order.order_type {
                OrderType::Market => "market",
                OrderType::Limit => "limit",
                _ => "market",
            },
            "side": match order.side {
                OrderSide::Buy => "buy",
                OrderSide::Sell => "sell",
            },
            "product_id": order.symbol,
            "size": order.quantity.to_string(),
            "price": order.price.map(|p| p.to_string()),
            "time_in_force": match order.time_in_force {
                TimeInForce::GTC => "GTC",
                TimeInForce::IOC => "IOC",
                TimeInForce::FOK => "FOK",
                _ => "GTC",
            },
        });
        
        let response = self.make_request("POST", "/orders", Some(order_data)).await?;
        
        Ok(OrderResponse {
            order_id: response["id"].as_str().unwrap_or("").to_string(),
            client_order_id: response["id"].as_str().unwrap_or("").to_string(),
            symbol: order.symbol,
            status: OrderStatus::New,
            created_at: chrono::Utc::now(),
        })
    }
    
    async fn cancel_order(&self, order_id: &str) -> Result<()> {
        let path = format!("/orders/{}", order_id);
        self.make_request("DELETE", &path, None).await?;
        Ok(())
    }
    
    async fn cancel_all_orders(&self) -> Result<()> {
        self.make_request("DELETE", "/orders", None).await?;
        Ok(())
    }
    
    async fn get_order_status(&self, order_id: &str) -> Result<OrderFill> {
        let path = format!("/orders/{}", order_id);
        let response = self.make_request("GET", &path, None).await?;
        
        let status = match response["status"].as_str().unwrap_or("") {
            "open" => OrderStatus::New,
            "done" => OrderStatus::Filled,
            "cancelled" => OrderStatus::Cancelled,
            "rejected" => OrderStatus::Rejected,
            _ => OrderStatus::New,
        };
        
        Ok(OrderFill {
            order_id: order_id.to_string(),
            symbol: response["product_id"].as_str().unwrap_or("").to_string(),
            side: if response["side"].as_str() == Some("buy") { OrderSide::Buy } else { OrderSide::Sell },
            status,
            filled_quantity: response["filled_size"].as_str().unwrap_or("0").parse().unwrap_or(0.0),
            average_price: response["executed_value"].as_str().unwrap_or("0").parse::<f64>().unwrap_or(0.0) / 
                          response["filled_size"].as_str().unwrap_or("1").parse::<f64>().unwrap_or(1.0),
            commission: response["fill_fees"].as_str().unwrap_or("0").parse().unwrap_or(0.0),
            commission_asset: "USD".to_string(),
            created_at: chrono::Utc::now(),
            updated_at: chrono::Utc::now(),
        })
    }
    
    async fn get_open_orders(&self) -> Result<Vec<OrderFill>> {
        let response = self.make_request("GET", "/orders?status=open", None).await?;
        // Implementation would parse the response array
        Ok(Vec::new())
    }
    
    async fn get_order_history(&self, _symbol: Option<&str>) -> Result<Vec<OrderFill>> {
        let response = self.make_request("GET", "/orders?status=done", None).await?;
        // Implementation would parse the response array
        Ok(Vec::new())
    }
    
    async fn get_trading_fees(&self) -> Result<TradingFees> {
        Ok(TradingFees {
            maker_fee: 0.005, // 0.5%
            taker_fee: 0.006, // 0.6%
            currency: "USD".to_string(),
        })
    }
}
