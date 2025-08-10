use anyhow::Result;
use hmac::{Hmac, Mac};
use sha2::Sha256;
use std::time::{SystemTime, UNIX_EPOCH};

pub struct BinanceConnector {
    api_key: String,
    secret: String,
    client: reqwest::Client,
}

impl BinanceConnector {
    pub fn new(api_key: String, secret: String) -> Self {
        Self { api_key, secret, client: reqwest::Client::new() }
    }

    pub async fn get_price(&self, symbol: &str) -> Result<f64> {
        let url = format!("https://api.binance.com/api/v3/ticker/price?symbol={}", symbol);
        let resp: serde_json::Value = self.client.get(&url).send().await?.json().await?;
        Ok(resp["price"].as_str().unwrap().parse()?)
    }

    pub async fn place_order(&self, symbol: &str, side: &str, amount: f64, price: f64) -> Result<String> {
        let timestamp = SystemTime::now().duration_since(UNIX_EPOCH)?.as_millis();
        let query = format!("symbol={}&side={}&type=LIMIT&timeInForce=GTC&quantity={}&price={}&timestamp={}", 
            symbol, side, amount, price, timestamp);
        
        let mut mac = Hmac::<Sha256>::new_from_slice(self.secret.as_bytes())?;
        mac.update(query.as_bytes());
        let signature = hex::encode(mac.finalize().into_bytes());
        
        let url = format!("https://api.binance.com/api/v3/order?{}&signature={}", query, signature);
        let resp: serde_json::Value = self.client
            .post(&url)
            .header("X-MBX-APIKEY", &self.api_key)
            .send().await?.json().await?;
        
        Ok(resp["orderId"].as_u64().unwrap().to_string())
    }
}
