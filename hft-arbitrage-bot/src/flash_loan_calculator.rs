use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct FlashLoanCosts {
    pub provider_fee_bps: u16,  // basis points (0.05% = 5 bps)
    pub gas_cost_usd: f64,
    pub execution_time_ms: u64,
    pub max_amount_usd: f64,
}

#[derive(Debug, Clone)]
pub struct ArbitrageProfit {
    pub gross_profit_usd: f64,
    pub flash_loan_fee: f64,
    pub gas_cost: f64,
    pub exchange_fees: f64,
    pub slippage_cost: f64,
    pub net_profit_usd: f64,
    pub roi_percentage: f64,
    pub execution_time_ms: u64,
    pub is_profitable: bool,
}

pub struct FlashLoanCalculator {
    providers: HashMap<String, FlashLoanCosts>,
    current_gas_price_gwei: u64,
    eth_price_usd: f64,
}

impl FlashLoanCalculator {
    pub fn new() -> Self {
        let mut providers = HashMap::new();
        
        // REAL flash loan providers with REAL costs
        providers.insert("aave_v3".to_string(), FlashLoanCosts {
            provider_fee_bps: 5,  // 0.05%
            gas_cost_usd: 0.0, // Calculated dynamically
            execution_time_ms: 15000, // ~1 block
            max_amount_usd: 50_000_000.0,
        });
        
        providers.insert("balancer_v2".to_string(), FlashLoanCosts {
            provider_fee_bps: 0,  // FREE!
            gas_cost_usd: 0.0,
            execution_time_ms: 15000,
            max_amount_usd: 20_000_000.0,
        });
        
        providers.insert("uniswap_v3".to_string(), FlashLoanCosts {
            provider_fee_bps: 0,  // FREE!
            gas_cost_usd: 0.0,
            execution_time_ms: 15000,
            max_amount_usd: 30_000_000.0,
        });
        
        providers.insert("dydx".to_string(), FlashLoanCosts {
            provider_fee_bps: 0,  // FREE!
            gas_cost_usd: 0.0,
            execution_time_ms: 15000,
            max_amount_usd: 5_000_000.0,
        });
        
        Self {
            providers,
            current_gas_price_gwei: 20, // Updated in real-time
            eth_price_usd: 2400.0, // Updated in real-time
        }
    }
    
    pub fn update_gas_conditions(&mut self, gas_price_gwei: u64, eth_price: f64) {
        self.current_gas_price_gwei = gas_price_gwei;
        self.eth_price_usd = eth_price;
        
        // Update gas costs for all providers
        let base_gas_cost = self.calculate_gas_cost_usd(500_000); // ~500k gas for arbitrage
        for provider in self.providers.values_mut() {
            provider.gas_cost_usd = base_gas_cost;
        }
    }
    
    fn calculate_gas_cost_usd(&self, gas_units: u64) -> f64 {
        let gas_cost_eth = (self.current_gas_price_gwei as f64 * gas_units as f64) / 1_000_000_000.0;
        gas_cost_eth * self.eth_price_usd
    }
    
    pub fn calculate_flash_arbitrage_profit(
        &self,
        buy_price: f64,
        sell_price: f64,
        trade_size_usd: f64,
        buy_exchange_fee_bps: u16,
        sell_exchange_fee_bps: u16,
    ) -> HashMap<String, ArbitrageProfit> {
        let mut results = HashMap::new();
        
        for (provider_name, provider) in &self.providers {
            if trade_size_usd > provider.max_amount_usd {
                continue; // Too large for this provider
            }
            
            // Calculate all costs
            let gross_profit_usd = ((sell_price - buy_price) / buy_price) * trade_size_usd;
            
            let flash_loan_fee = if provider.provider_fee_bps > 0 {
                (provider.provider_fee_bps as f64 / 10000.0) * trade_size_usd
            } else {
                0.0
            };
            
            let gas_cost = provider.gas_cost_usd;
            
            // Exchange fees (buy + sell)
            let buy_fee = (buy_exchange_fee_bps as f64 / 10000.0) * trade_size_usd;
            let sell_fee = (sell_exchange_fee_bps as f64 / 10000.0) * trade_size_usd;
            let exchange_fees = buy_fee + sell_fee;
            
            // Slippage estimate (0.1% for liquid pairs, more for illiquid)
            let slippage_cost = 0.001 * trade_size_usd;
            
            // Net profit calculation
            let total_costs = flash_loan_fee + gas_cost + exchange_fees + slippage_cost;
            let net_profit_usd = gross_profit_usd - total_costs;
            
            let roi_percentage = if trade_size_usd > 0.0 {
                (net_profit_usd / trade_size_usd) * 100.0
            } else {
                0.0
            };
            
            let is_profitable = net_profit_usd > 0.0 && roi_percentage > 0.01; // Min 0.01% ROI
            
            results.insert(provider_name.clone(), ArbitrageProfit {
                gross_profit_usd,
                flash_loan_fee,
                gas_cost,
                exchange_fees,
                slippage_cost,
                net_profit_usd,
                roi_percentage,
                execution_time_ms: provider.execution_time_ms,
                is_profitable,
            });
        }
        
        results
    }
    
    pub fn find_best_flash_loan_provider(&self, trade_size_usd: f64) -> Option<String> {
        let mut best_provider = None;
        let mut lowest_cost = f64::MAX;
        
        for (provider_name, provider) in &self.providers {
            if trade_size_usd <= provider.max_amount_usd {
                let total_cost = provider.gas_cost_usd + 
                    (provider.provider_fee_bps as f64 / 10000.0) * trade_size_usd;
                
                if total_cost < lowest_cost {
                    lowest_cost = total_cost;
                    best_provider = Some(provider_name.clone());
                }
            }
        }
        
        best_provider
    }
    
    pub fn calculate_minimum_profitable_spread(&self, trade_size_usd: f64) -> f64 {
        if let Some(best_provider) = self.find_best_flash_loan_provider(trade_size_usd) {
            if let Some(provider) = self.providers.get(&best_provider) {
                // Calculate total costs
                let flash_loan_fee = (provider.provider_fee_bps as f64 / 10000.0) * trade_size_usd;
                let gas_cost = provider.gas_cost_usd;
                let exchange_fees = 0.002 * trade_size_usd; // 0.2% total (0.1% each side)
                let slippage = 0.001 * trade_size_usd; // 0.1%
                
                let total_costs = flash_loan_fee + gas_cost + exchange_fees + slippage;
                
                // Minimum spread needed to break even
                return (total_costs / trade_size_usd) * 100.0;
            }
        }
        
        1.0 // Default 1% if calculation fails
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_flash_loan_profitability() {
        let mut calculator = FlashLoanCalculator::new();
        calculator.update_gas_conditions(30, 2400.0); // 30 gwei, $2400 ETH
        
        // Test case: 0.5% price difference on $10k trade
        let buy_price = 100.0;
        let sell_price = 100.5; // 0.5% higher
        let trade_size = 10_000.0;
        
        let results = calculator.calculate_flash_arbitrage_profit(
            buy_price,
            sell_price,
            trade_size,
            10, // 0.1% buy fee
            10, // 0.1% sell fee
        );
        
        for (provider, profit) in results {
            println!("{}: Net profit: ${:.2}, ROI: {:.3}%, Profitable: {}", 
                     provider, profit.net_profit_usd, profit.roi_percentage, profit.is_profitable);
        }
        
        // Should be profitable with Balancer (no fees)
        assert!(results.get("balancer_v2").unwrap().is_profitable);
    }
    
    #[test]
    fn test_minimum_spread_calculation() {
        let mut calculator = FlashLoanCalculator::new();
        calculator.update_gas_conditions(50, 2400.0); // Higher gas
        
        let min_spread = calculator.calculate_minimum_profitable_spread(10_000.0);
        println!("Minimum profitable spread: {:.3}%", min_spread);
        
        assert!(min_spread > 0.0);
        assert!(min_spread < 2.0); // Should be reasonable
    }
}
