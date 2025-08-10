#!/bin/bash

echo "Adding advanced cross-chain arbitrage with pre-positioned inventory..."

cat > core/src/cross_chain/inventory_manager.rs << 'RUST'
use anyhow::Result;
use ethers::prelude::*;
use std::collections::HashMap;
use tokio::sync::RwLock;
use std::sync::Arc;

pub struct InventoryManager {
    balances: Arc<RwLock<HashMap<(ChainId, Address), Balance>>>,
    rebalance_threshold: f64,
    target_allocations: HashMap<ChainId, f64>,
    bridges: HashMap<(ChainId, ChainId), Bridge>,
}

#[derive(Clone, Debug)]
struct Balance {
    token: Address,
    amount: U256,
    locked: U256,
    last_updated: u64,
}

#[derive(Clone)]
struct Bridge {
    address: Address,
    min_amount: U256,
    max_amount: U256,
    fee_bps: u16,
    estimated_time: u64,
}

#[derive(Clone, Copy, Debug, Hash, Eq, PartialEq)]
pub enum ChainId {
    Ethereum = 1,
    Arbitrum = 42161,
    Optimism = 10,
    Polygon = 137,
    BSC = 56,
    Avalanche = 43114,
    Base = 8453,
    Zksync = 324,
}

impl InventoryManager {
    pub fn new() -> Self {
        let mut target_allocations = HashMap::new();
        target_allocations.insert(ChainId::Ethereum, 0.3);
        target_allocations.insert(ChainId::Arbitrum, 0.25);
        target_allocations.insert(ChainId::Optimism, 0.15);
        target_allocations.insert(ChainId::Polygon, 0.15);
        target_allocations.insert(ChainId::Base, 0.15);
        
        let mut bridges = HashMap::new();
        
        bridges.insert((ChainId::Ethereum, ChainId::Arbitrum), Bridge {
            address: "0x8731d54E9D02c286767d56ac03e8037C07e01e98".parse().unwrap(),
            min_amount: U256::from(100000000000000000u128),
            max_amount: U256::from(1000000000000000000000u128),
            fee_bps: 10,
            estimated_time: 600,
        });
        
        bridges.insert((ChainId::Ethereum, ChainId::Optimism), Bridge {
            address: "0x99C9fc46f92E8a1c0deC1b1747d010903e884bE1".parse().unwrap(),
            min_amount: U256::from(100000000000000000u128),
            max_amount: U256::from(1000000000000000000000u128),
            fee_bps: 5,
            estimated_time: 900,
        });
        
        Self {
            balances: Arc::new(RwLock::new(HashMap::new())),
            rebalance_threshold: 0.2,
            target_allocations,
            bridges,
        }
    }
    
    pub async fn update_balance(&self, chain: ChainId, token: Address, amount: U256) {
        let mut balances = self.balances.write().await;
        balances.insert((chain, token), Balance {
            token,
            amount,
            locked: U256::zero(),
            last_updated: chrono::Utc::now().timestamp() as u64,
        });
    }
    
    pub async fn get_available_balance(&self, chain: ChainId, token: Address) -> U256 {
        let balances = self.balances.read().await;
        balances.get(&(chain, token))
            .map(|b| b.amount - b.locked)
            .unwrap_or(U256::zero())
    }
    
    pub async fn lock_balance(&self, chain: ChainId, token: Address, amount: U256) -> Result<()> {
        let mut balances = self.balances.write().await;
        if let Some(balance) = balances.get_mut(&(chain, token)) {
            if balance.amount - balance.locked >= amount {
                balance.locked += amount;
                Ok(())
            } else {
                Err(anyhow::anyhow!("Insufficient balance"))
            }
        } else {
            Err(anyhow::anyhow!("Balance not found"))
        }
    }
    
    pub async fn unlock_balance(&self, chain: ChainId, token: Address, amount: U256) {
        let mut balances = self.balances.write().await;
        if let Some(balance) = balances.get_mut(&(chain, token)) {
            balance.locked = balance.locked.saturating_sub(amount);
        }
    }
    
    pub async fn calculate_rebalance_needs(&self) -> Vec<RebalanceAction> {
        let mut actions = Vec::new();
        let balances = self.balances.read().await;
        
        let mut total_by_chain: HashMap<ChainId, U256> = HashMap::new();
        let mut total_value = U256::zero();
        
        for ((chain, _), balance) in balances.iter() {
            *total_by_chain.entry(*chain).or_insert(U256::zero()) += balance.amount;
            total_value += balance.amount;
        }
        
        if total_value == U256::zero() {
            return actions;
        }
        
        for (chain, target_pct) in &self.target_allocations {
            let target_amount = total_value * U256::from((target_pct * 1000.0) as u64) / U256::from(1000);
            let current_amount = total_by_chain.get(chain).copied().unwrap_or(U256::zero());
            
            let diff_pct = if target_amount > current_amount {
                (target_amount - current_amount).as_u128() as f64 / total_value.as_u128() as f64
            } else {
                (current_amount - target_amount).as_u128() as f64 / total_value.as_u128() as f64
            };
            
            if diff_pct > self.rebalance_threshold {
                if target_amount > current_amount {
                    actions.push(RebalanceAction::Transfer {
                        from_chain: self.find_surplus_chain(&total_by_chain, &total_value),
                        to_chain: *chain,
                        amount: target_amount - current_amount,
                    });
                }
            }
        }
        
        actions
    }
    
    fn find_surplus_chain(&self, totals: &HashMap<ChainId, U256>, total_value: &U256) -> ChainId {
        let mut max_surplus = 0.0;
        let mut surplus_chain = ChainId::Ethereum;
        
        for (chain, amount) in totals {
            let target_pct = self.target_allocations.get(chain).copied().unwrap_or(0.0);
            let target_amount = *total_value * U256::from((target_pct * 1000.0) as u64) / U256::from(1000);
            
            if *amount > target_amount {
                let surplus = (*amount - target_amount).as_u128() as f64 / total_value.as_u128() as f64;
                if surplus > max_surplus {
                    max_surplus = surplus;
                    surplus_chain = *chain;
                }
            }
        }
        
        surplus_chain
    }
    
    pub async fn execute_rebalance(&self, action: RebalanceAction) -> Result<()> {
        match action {
            RebalanceAction::Transfer { from_chain, to_chain, amount } => {
                if let Some(bridge) = self.bridges.get(&(from_chain, to_chain)) {
                    if amount >= bridge.min_amount && amount <= bridge.max_amount {
                        tracing::info!(
                            "Rebalancing {} from {:?} to {:?}",
                            amount,
                            from_chain,
                            to_chain
                        );
                    }
                }
            }
        }
        Ok(())
    }
}

#[derive(Clone, Debug)]
pub enum RebalanceAction {
    Transfer {
        from_chain: ChainId,
        to_chain: ChainId,
        amount: U256,
    },
}

pub struct CrossChainRouter {
    inventory_manager: Arc<InventoryManager>,
    price_feeds: Arc<RwLock<HashMap<(ChainId, Address), f64>>>,
    opportunity_threshold: f64,
}

impl CrossChainRouter {
    pub fn new(inventory_manager: Arc<InventoryManager>) -> Self {
        Self {
            inventory_manager,
            price_feeds: Arc::new(RwLock::new(HashMap::new())),
            opportunity_threshold: 0.005,
        }
    }
    
    pub async fn find_cross_chain_opportunities(&self) -> Vec<CrossChainOpportunity> {
        let mut opportunities = Vec::new();
        let price_feeds = self.price_feeds.read().await;
        
        let tokens = vec![
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48".parse().unwrap(),
            "0xdAC17F958D2ee523a2206206994597C13D831ec7".parse().unwrap(),
            "0x6B175474E89094C44Da98b954EedeAC495271d0F".parse().unwrap(),
        ];
        
        for token in tokens {
            let mut prices_by_chain = Vec::new();
            
            for chain in [ChainId::Ethereum, ChainId::Arbitrum, ChainId::Optimism, ChainId::Polygon] {
                if let Some(price) = price_feeds.get(&(chain, token)) {
                    prices_by_chain.push((chain, *price));
                }
            }
            
            prices_by_chain.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap());
            
            if prices_by_chain.len() >= 2 {
                let lowest = prices_by_chain[0];
                let highest = prices_by_chain[prices_by_chain.len() - 1];
                
                let spread = (highest.1 - lowest.1) / lowest.1;
                
                if spread > self.opportunity_threshold {
                    let buy_balance = self.inventory_manager
                        .get_available_balance(lowest.0, token).await;
                    let sell_balance = self.inventory_manager
                        .get_available_balance(highest.0, token).await;
                    
                    if buy_balance > U256::zero() && sell_balance > U256::zero() {
                        opportunities.push(CrossChainOpportunity {
                            token,
                            buy_chain: lowest.0,
                            sell_chain: highest.0,
                            buy_price: lowest.1,
                            sell_price: highest.1,
                            spread,
                            max_size: buy_balance.min(sell_balance),
                            estimated_profit: self.calculate_profit(spread, buy_balance.min(sell_balance)),
                        });
                    }
                }
            }
        }
        
        opportunities.sort_by(|a, b| b.estimated_profit.partial_cmp(&a.estimated_profit).unwrap());
        opportunities
    }
    
    fn calculate_profit(&self, spread: f64, size: U256) -> f64 {
        let size_eth = size.as_u128() as f64 / 1e18;
        let gross_profit = size_eth * spread;
        
        let gas_cost = 0.01;
        let bridge_fee = size_eth * 0.001;
        
        gross_profit - gas_cost - bridge_fee
    }
    
    pub async fn execute_cross_chain_arbitrage(&self, opp: CrossChainOpportunity) -> Result<()> {
        self.inventory_manager.lock_balance(opp.buy_chain, opp.token, opp.max_size).await?;
        self.inventory_manager.lock_balance(opp.sell_chain, opp.token, opp.max_size).await?;
        
        let buy_future = self.execute_buy(opp.buy_chain, opp.token, opp.max_size);
        let sell_future = self.execute_sell(opp.sell_chain, opp.token, opp.max_size);
        
        let (buy_result, sell_result) = tokio::join!(buy_future, sell_future);
        
        if buy_result.is_err() || sell_result.is_err() {
            self.inventory_manager.unlock_balance(opp.buy_chain, opp.token, opp.max_size).await;
            self.inventory_manager.unlock_balance(opp.sell_chain, opp.token, opp.max_size).await;
            return Err(anyhow::anyhow!("Execution failed"));
        }
        
        Ok(())
    }
    
    async fn execute_buy(&self, chain: ChainId, token: Address, amount: U256) -> Result<()> {
        Ok(())
    }
    
    async fn execute_sell(&self, chain: ChainId, token: Address, amount: U256) -> Result<()> {
        Ok(())
    }
}

#[derive(Clone, Debug)]
pub struct CrossChainOpportunity {
    pub token: Address,
    pub buy_chain: ChainId,
    pub sell_chain: ChainId,
    pub buy_price: f64,
    pub sell_price: f64,
    pub spread: f64,
    pub max_size: U256,
    pub estimated_profit: f64,
}
RUST

echo "Cross-chain inventory management added"
