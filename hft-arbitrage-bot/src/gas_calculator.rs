use anyhow::Result;
use reqwest::Client;
use serde_json::Value;
use std::time::Duration;
use tracing::{info, warn, debug};

pub struct GasCalculator {
    client: Client,
    current_gas_price_gwei: f64,
    eth_price_usd: f64,
}

impl GasCalculator {
    pub fn new() -> Self {
        Self {
            client: Client::builder()
                .timeout(Duration::from_secs(10))
                .build()
                .expect("Failed to create HTTP client"),
            current_gas_price_gwei: 20.0, // Default 20 gwei
            eth_price_usd: 2500.0, // Default ETH price
        }
    }

    pub async fn initialize(&mut self) -> Result<()> {
        info!("⛽ Initializing gas calculator with real data...");
        
        // Fetch real gas prices
        self.update_gas_prices().await?;
        
        // Fetch real ETH price
        self.update_eth_price().await?;
        
        info!("✅ Gas calculator initialized - {} gwei, ETH ${:.2}", 
              self.current_gas_price_gwei, self.eth_price_usd);
        
        Ok(())
    }

    async fn update_gas_prices(&mut self) -> Result<()> {
        // Try multiple gas price APIs
        let gas_apis = vec![
            "https://api.etherscan.io/api?module=gastracker&action=gasoracle",
            "https://gas-api.metaswap.codefi.network/networks/1/suggestedGasFees",
        ];

        for api_url in gas_apis {
            match self.fetch_gas_price(api_url).await {
                Ok(gas_price) => {
                    self.current_gas_price_gwei = gas_price;
                    debug!("✅ Updated gas price: {} gwei from {}", gas_price, api_url);
                    return Ok(());
                }
                Err(e) => {
                    warn!("❌ Failed to fetch gas from {}: {}", api_url, e);
                    continue;
                }
            }
        }

        warn!("⚠️  Using default gas price: {} gwei", self.current_gas_price_gwei);
        Ok(())
    }

    async fn fetch_gas_price(&self, url: &str) -> Result<f64> {
        let response = self.client.get(url).send().await?;
        let data: Value = response.json().await?;

        // Parse different API formats
        if let Some(result) = data.get("result") {
            // Etherscan format
            if let Some(standard) = result.get("ProposeGasPrice") {
                return Ok(standard.as_str().unwrap_or("20").parse()?);
            }
        } else if let Some(medium) = data.get("medium") {
            // MetaMask format
            if let Some(suggested) = medium.get("suggestedMaxFeePerGas") {
                return Ok(suggested.as_str().unwrap_or("20").parse()?);
            }
        }

        Err(anyhow::anyhow!("Failed to parse gas price response"))
    }

    async fn update_eth_price(&mut self) -> Result<()> {
        let url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd";
        
        match self.client.get(url).send().await {
            Ok(response) => {
                if let Ok(data) = response.json::<Value>().await {
                    if let Some(eth_data) = data.get("ethereum") {
                        if let Some(usd_price) = eth_data.get("usd") {
                            self.eth_price_usd = usd_price.as_f64().unwrap_or(2500.0);
                            debug!("✅ Updated ETH price: ${:.2}", self.eth_price_usd);
                            return Ok(());
                        }
                    }
                }
            }
            Err(e) => {
                warn!("❌ Failed to fetch ETH price: {}", e);
            }
        }

        warn!("⚠️  Using default ETH price: ${:.2}", self.eth_price_usd);
        Ok(())
    }

    pub async fn estimate_arbitrage_gas_cost(&self) -> Result<f64> {
        // Estimate gas usage for arbitrage transactions
        let swap_gas = 150_000u64; // DEX swap
        let transfer_gas = 21_000u64; // ETH transfer
        let flash_loan_gas = 200_000u64; // Flash loan overhead
        
        let total_gas = swap_gas * 2 + transfer_gas + flash_loan_gas; // Buy + Sell + Transfer + Flash loan
        
        let gas_cost_eth = (total_gas as f64 * self.current_gas_price_gwei) / 1_000_000_000.0;
        let gas_cost_usd = gas_cost_eth * self.eth_price_usd;
        
        debug!("⛽ Estimated gas cost: {} ETH (${:.2}) for {} gas @ {} gwei", 
               gas_cost_eth, gas_cost_usd, total_gas, self.current_gas_price_gwei);
        
        Ok(gas_cost_usd)
    }

    #[allow(dead_code)]
    pub async fn estimate_flash_loan_gas(&self) -> Result<f64> {
        // Flash loan specific gas estimation
        let flash_loan_setup = 100_000u64;
        let arbitrage_execution = 300_000u64;
        let flash_loan_repay = 50_000u64;
        
        let total_gas = flash_loan_setup + arbitrage_execution + flash_loan_repay;
        
        let gas_cost_eth = (total_gas as f64 * self.current_gas_price_gwei) / 1_000_000_000.0;
        let gas_cost_usd = gas_cost_eth * self.eth_price_usd;
        
        debug!("⚡ Flash loan gas cost: {} ETH (${:.2})", gas_cost_eth, gas_cost_usd);
        
        Ok(gas_cost_usd)
    }

    #[allow(dead_code)]
    pub fn get_current_gas_price(&self) -> f64 {
        self.current_gas_price_gwei
    }

    #[allow(dead_code)]
    pub fn get_eth_price(&self) -> f64 {
        self.eth_price_usd
    }
}
