use anyhow::Result;
use reqwest::Client;

pub struct AlertManager {
    webhook_url: String,
    client: Client,
}

impl AlertManager {
    pub fn new(webhook_url: String) -> Self {
        Self { webhook_url, client: Client::new() }
    }

    pub async fn send_profit_alert(&self, amount: f64, opportunity: &str) -> Result<()> {
        let payload = serde_json::json!({
            "text": format!("💰 Profit Alert: ${:.2} from {}", amount, opportunity),
            "channel": "#arbitrage",
            "username": "ArbitrageBot"
        });
        
        self.client.post(&self.webhook_url).json(&payload).send().await?;
        Ok(())
    }

    pub async fn send_error_alert(&self, error: &str) -> Result<()> {
        let payload = serde_json::json!({
            "text": format!("🚨 Error: {}", error),
            "channel": "#arbitrage-alerts",
            "username": "ArbitrageBot"
        });
        
        self.client.post(&self.webhook_url).json(&payload).send().await?;
        Ok(())
    }
}
