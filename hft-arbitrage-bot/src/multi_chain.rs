use std::collections::HashMap;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone)]
pub struct ChainConfig {
    pub chain_id: u64,
    pub rpc_url: String,
    pub gas_token: String,
    pub avg_block_time_ms: u64,
    pub flash_loan_providers: Vec<String>,
    pub major_dexes: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct CrossChainOpportunity {
    pub source_chain: String,
    pub target_chain: String,
    pub token: String,
    pub source_price: f64,
    pub target_price: f64,
    pub bridge_cost: f64,
    pub bridge_time_seconds: u64,
    pub profit_after_costs: f64,
}

pub struct MultiChainEngine {
    chains: HashMap<String, ChainConfig>,
    bridge_costs: HashMap<(String, String), f64>, // (from, to) -> cost %
}

impl MultiChainEngine {
    pub fn new() -> Self {
        let mut chains = HashMap::new();
        
        // Ethereum L1
        chains.insert("ethereum".to_string(), ChainConfig {
            chain_id: 1,
            rpc_url: "wss://mainnet.infura.io/ws/v3/YOUR_KEY".to_string(),
            gas_token: "ETH".to_string(),
            avg_block_time_ms: 12000,
            flash_loan_providers: vec!["aave".to_string(), "balancer".to_string()],
            major_dexes: vec!["uniswap_v3".to_string(), "sushiswap".to_string()],
        });
        
        // Arbitrum L2
        chains.insert("arbitrum".to_string(), ChainConfig {
            chain_id: 42161,
            rpc_url: "wss://arb1.arbitrum.io/ws".to_string(),
            gas_token: "ETH".to_string(),
            avg_block_time_ms: 300, // ~300ms blocks
            flash_loan_providers: vec!["aave_arbitrum".to_string()],
            major_dexes: vec!["uniswap_v3_arb".to_string(), "camelot".to_string()],
        });
        
        // Polygon L2
        chains.insert("polygon".to_string(), ChainConfig {
            chain_id: 137,
            rpc_url: "wss://polygon-rpc.com/".to_string(),
            gas_token: "MATIC".to_string(),
            avg_block_time_ms: 2000,
            flash_loan_providers: vec!["aave_polygon".to_string()],
            major_dexes: vec!["quickswap".to_string(), "sushiswap_polygon".to_string()],
        });
        
        // Base L2
        chains.insert("base".to_string(), ChainConfig {
            chain_id: 8453,
            rpc_url: "wss://mainnet.base.org".to_string(),
            gas_token: "ETH".to_string(),
            avg_block_time_ms: 2000,
            flash_loan_providers: vec!["aave_base".to_string()],
            major_dexes: vec!["uniswap_v3_base".to_string(), "baseswap".to_string()],
        });
        
        // Solana L1
        chains.insert("solana".to_string(), ChainConfig {
            chain_id: 0, // Solana doesn't use chain IDs
            rpc_url: "wss://api.mainnet-beta.solana.com/".to_string(),
            gas_token: "SOL".to_string(),
            avg_block_time_ms: 400,
            flash_loan_providers: vec!["solend".to_string()],
            major_dexes: vec!["jupiter".to_string(), "raydium".to_string()],
        });
        
        // Avalanche L1
        chains.insert("avalanche".to_string(), ChainConfig {
            chain_id: 43114,
            rpc_url: "wss://api.avax.network/ext/bc/C/ws".to_string(),
            gas_token: "AVAX".to_string(),
            avg_block_time_ms: 3000,
            flash_loan_providers: vec!["aave_avalanche".to_string()],
            major_dexes: vec!["traderjoe".to_string(), "pangolin".to_string()],
        });

        let mut bridge_costs = HashMap::new();
        
        // Cross-chain bridge costs (percentage)
        bridge_costs.insert(("ethereum".to_string(), "arbitrum".to_string()), 0.01); // 0.01%
        bridge_costs.insert(("ethereum".to_string(), "polygon".to_string()), 0.02);
        bridge_costs.insert(("ethereum".to_string(), "base".to_string()), 0.01);
        bridge_costs.insert(("arbitrum".to_string(), "ethereum".to_string()), 0.01);
        bridge_costs.insert(("polygon".to_string(), "ethereum".to_string()), 0.02);
        bridge_costs.insert(("solana".to_string(), "ethereum".to_string()), 0.05); // Higher for different L1s
        
        Self { chains, bridge_costs }
    }
    
    pub fn find_cross_chain_opportunities(&self, token: &str, prices: &HashMap<String, f64>) -> Vec<CrossChainOpportunity> {
        let mut opportunities = Vec::new();
        
        for (source_chain, source_price) in prices {
            for (target_chain, target_price) in prices {
                if source_chain == target_chain {
                    continue;
                }
                
                let bridge_cost = self.bridge_costs
                    .get(&(source_chain.clone(), target_chain.clone()))
                    .unwrap_or(&0.1); // Default 0.1% if not specified
                
                if target_price > source_price {
                    let gross_profit_pct = ((target_price - source_price) / source_price) * 100.0;
                    let bridge_cost_pct = bridge_cost * 100.0;
                    let net_profit_pct = gross_profit_pct - bridge_cost_pct;
                    
                    if net_profit_pct > 0.05 { // Minimum 0.05% after bridge costs
                        let bridge_time = self.estimate_bridge_time(source_chain, target_chain);
                        
                        opportunities.push(CrossChainOpportunity {
                            source_chain: source_chain.clone(),
                            target_chain: target_chain.clone(),
                            token: token.to_string(),
                            source_price: *source_price,
                            target_price: *target_price,
                            bridge_cost: *bridge_cost,
                            bridge_time_seconds: bridge_time,
                            profit_after_costs: net_profit_pct,
                        });
                    }
                }
            }
        }
        
        opportunities.sort_by(|a, b| b.profit_after_costs.partial_cmp(&a.profit_after_costs).unwrap());
        opportunities
    }
    
    fn estimate_bridge_time(&self, from: &str, to: &str) -> u64 {
        match (from, to) {
            ("ethereum", "arbitrum") => 600,      // ~10 minutes
            ("arbitrum", "ethereum") => 604800,   // ~7 days (withdrawal period)
            ("ethereum", "polygon") => 1800,      // ~30 minutes
            ("polygon", "ethereum") => 3600,      // ~1 hour
            ("ethereum", "base") => 1200,         // ~20 minutes
            ("solana", "ethereum") => 600,        // ~10 minutes via Wormhole
            _ => 3600, // Default 1 hour
        }
    }
    
    pub async fn execute_cross_chain_arbitrage(&self, opportunity: &CrossChainOpportunity) -> Result<bool, String> {
        // Implementation would:
        // 1. Flash loan on source chain
        // 2. Buy token on source chain
        // 3. Bridge token to target chain
        // 4. Sell token on target chain
        // 5. Bridge proceeds back
        // 6. Repay flash loan
        
        tracing::info!("Executing cross-chain arbitrage: {} -> {}", 
                      opportunity.source_chain, opportunity.target_chain);
        
        // For now, simulate execution
        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
        
        Ok(true)
    }
    
    pub fn get_supported_chains(&self) -> Vec<String> {
        self.chains.keys().cloned().collect()
    }
    
    pub fn get_flash_loan_providers(&self, chain: &str) -> Vec<String> {
        self.chains.get(chain)
            .map(|config| config.flash_loan_providers.clone())
            .unwrap_or_default()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_cross_chain_opportunities() {
        let engine = MultiChainEngine::new();
        
        let mut prices = HashMap::new();
        prices.insert("ethereum".to_string(), 2000.0);
        prices.insert("arbitrum".to_string(), 2010.0); // 0.5% higher
        prices.insert("polygon".to_string(), 1995.0);   // 0.25% lower
        
        let opportunities = engine.find_cross_chain_opportunities("ETH", &prices);
        
        assert!(!opportunities.is_empty());
        assert!(opportunities[0].profit_after_costs > 0.0);
    }
}
