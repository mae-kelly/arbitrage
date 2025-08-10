use super::*;
use tokio::sync::RwLock;
use std::sync::Arc;

pub struct InventoryManager {
    balances: Arc<RwLock<HashMap<(ChainId, Address), Balance>>>,
    rebalance_threshold: f64,
}

#[derive(Clone, Debug)]
struct Balance {
    token: Address,
    amount: U256,
    locked: U256,
}

impl InventoryManager {
    pub fn new() -> Self {
        Self {
            balances: Arc::new(RwLock::new(HashMap::new())),
            rebalance_threshold: 0.2,
        }
    }
    
    pub async fn get_balance(&self, chain: ChainId, token: Address) -> U256 {
        let balances = self.balances.read().await;
        balances.get(&(chain, token))
            .map(|b| b.amount - b.locked)
            .unwrap_or(U256::zero())
    }
    
    pub async fn update_balance(&self, chain: ChainId, token: Address, amount: U256) {
        let mut balances = self.balances.write().await;
        balances.entry((chain, token))
            .and_modify(|b| b.amount = amount)
            .or_insert(Balance {
                token,
                amount,
                locked: U256::zero(),
            });
    }
}
