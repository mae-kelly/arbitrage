use std::collections::HashMap;

#[derive(Clone)]
pub struct FlashLoanProvider {
    pub name: String,
    pub fee_bps: u16, // basis points
    pub max_amount: f64,
    pub gas_cost: u64,
}

#[derive(Clone)]
pub struct FlashLoanArbitrage {
    pub provider: String,
    pub amount: f64,
    pub token: String,
    pub buy_exchange: String,
    pub sell_exchange: String,
    pub gross_profit: f64,
    pub flash_fee: f64,
    pub gas_cost: f64,
    pub net_profit: f64,
}

pub struct FlashLoanEngine {
    providers: HashMap<String, FlashLoanProvider>,
}

impl FlashLoanEngine {
    pub fn new() -> Self {
        let mut providers = HashMap::new();
        
        providers.insert("aave".to_string(), FlashLoanProvider {
            name: "Aave V3".to_string(),
            fee_bps: 5, // 0.05%
            max_amount: 10_000_000.0,
            gas_cost: 400_000,
        });
        
        providers.insert("balancer".to_string(), FlashLoanProvider {
            name: "Balancer V2".to_string(),
            fee_bps: 0, // FREE!
            max_amount: 5_000_000.0,
            gas_cost: 300_000,
        });
        
        providers.insert("dydx".to_string(), FlashLoanProvider {
            name: "dYdX".to_string(),
            fee_bps: 0, // FREE!
            max_amount: 1_000_000.0,
            gas_cost: 450_000,
        });

        Self { providers }
    }

    pub fn calculate_flash_arbitrage(&self, 
        token: &str, 
        amount: f64,
        buy_price: f64, 
        sell_price: f64,
        buy_exchange: &str,
        sell_exchange: &str,
        gas_price_gwei: u64) -> Option<FlashLoanArbitrage> {
        
        let gross_profit = (sell_price - buy_price) * amount;
        let mut best_arb: Option<FlashLoanArbitrage> = None;
        let mut best_net_profit = 0.0;

        for (provider_name, provider) in &self.providers {
            if amount > provider.max_amount { continue; }

            let flash_fee = amount * (provider.fee_bps as f64) / 10_000.0;
            let gas_cost_eth = (provider.gas_cost as f64) * (gas_price_gwei as f64) / 1e9;
            let gas_cost_usd = gas_cost_eth * 2000.0; // ETH price
            let net_profit = gross_profit - flash_fee - gas_cost_usd;

            if net_profit > best_net_profit && net_profit > 10.0 {
                best_net_profit = net_profit;
                best_arb = Some(FlashLoanArbitrage {
                    provider: provider_name.clone(),
                    amount,
                    token: token.to_string(),
                    buy_exchange: buy_exchange.to_string(),
                    sell_exchange: sell_exchange.to_string(),
                    gross_profit,
                    flash_fee,
                    gas_cost: gas_cost_usd,
                    net_profit,
                });
            }
        }

        best_arb
    }
}
