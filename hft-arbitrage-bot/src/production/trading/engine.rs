//! Production Trading Engine with Real Money Execution

use anyhow::Result;
use async_trait::async_trait;
use dashmap::DashMap;
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::{RwLock, Semaphore};
use tracing::{info, warn, error, debug};
use uuid::Uuid;

use crate::exchanges::authenticated::*;
use crate::portfolio::manager::PortfolioManager;
use crate::risk_management::advanced_risk::AdvancedRiskManager;

#[derive(Debug, Clone)]
pub struct ProductionTradingEngine {
    exchange_clients: Arc<DashMap<String, Box<dyn AuthenticatedExchange>>>,
    portfolio_manager: Arc<PortfolioManager>,
    risk_manager: Arc<AdvancedRiskManager>,
    order_manager: Arc<OrderManager>,
    execution_semaphore: Arc<Semaphore>,
    config: TradingConfig,
    metrics: Arc<TradingMetrics>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradingConfig {
    pub max_concurrent_orders: usize,
    pub max_position_size_usd: f64,
    pub max_daily_volume_usd: f64,
    pub paper_trading_mode: bool,
    pub require_manual_approval: bool,
    pub emergency_stop: bool,
}

#[derive(Debug, Default)]
pub struct TradingMetrics {
    pub total_orders: std::sync::atomic::AtomicU64,
    pub successful_orders: std::sync::atomic::AtomicU64,
    pub total_volume: std::sync::atomic::AtomicU64, // in cents
    pub total_profit: std::sync::atomic::AtomicI64, // in cents
}

impl ProductionTradingEngine {
    pub async fn new(config: TradingConfig) -> Result<Self> {
        info!("🚀 Initializing Production Trading Engine");
        
        let engine = Self {
            exchange_clients: Arc::new(DashMap::new()),
            portfolio_manager: Arc::new(PortfolioManager::new().await?),
            risk_manager: Arc::new(AdvancedRiskManager::new()),
            order_manager: Arc::new(OrderManager::new()),
            execution_semaphore: Arc::new(Semaphore::new(config.max_concurrent_orders)),
            config,
            metrics: Arc::new(TradingMetrics::default()),
        };
        
        info!("✅ Production Trading Engine initialized");
        Ok(engine)
    }
    
    pub async fn add_exchange(&self, name: String, client: Box<dyn AuthenticatedExchange>) -> Result<()> {
        info!("🔗 Adding exchange: {}", name);
        
        // Test connection
        client.test_connection().await?;
        
        self.exchange_clients.insert(name.clone(), client);
        info!("✅ Exchange {} added and tested", name);
        Ok(())
    }
    
    pub async fn execute_arbitrage_strategy(&self, strategy: ArbitrageStrategy) -> Result<ExecutionResult> {
        info!("⚡ Executing arbitrage strategy: {}", strategy.id);
        
        if self.config.emergency_stop {
            return Err(anyhow::anyhow!("Emergency stop activated"));
        }
        
        let _permit = self.execution_semaphore.acquire().await?;
        
        // Pre-execution validation
        self.validate_strategy(&strategy).await?;
        
        if self.config.paper_trading_mode {
            return self.execute_paper_arbitrage(&strategy).await;
        }
        
        if self.config.require_manual_approval {
            warn!("Manual approval required for strategy: {}", strategy.id);
            return Err(anyhow::anyhow!("Manual approval required"));
        }
        
        // Real execution
        self.execute_real_arbitrage(&strategy).await
    }
    
    async fn validate_strategy(&self, strategy: &ArbitrageStrategy) -> Result<()> {
        // Position size validation
        if strategy.position_size_usd > self.config.max_position_size_usd {
            return Err(anyhow::anyhow!("Position size exceeds limit"));
        }
        
        // Daily volume check
        let daily_volume = self.portfolio_manager.get_daily_volume().await?;
        if daily_volume + strategy.position_size_usd > self.config.max_daily_volume_usd {
            return Err(anyhow::anyhow!("Daily volume limit exceeded"));
        }
        
        // Risk management validation
        let portfolio_risk = self.risk_manager.calculate_portfolio_var(&[]).await?;
        if portfolio_risk > 10000.0 { // $10k VaR limit
            return Err(anyhow::anyhow!("Portfolio VaR too high"));
        }
        
        // Exchange availability
        if !self.exchange_clients.contains_key(&strategy.buy_exchange) {
            return Err(anyhow::anyhow!("Buy exchange not available: {}", strategy.buy_exchange));
        }
        
        if !self.exchange_clients.contains_key(&strategy.sell_exchange) {
            return Err(anyhow::anyhow!("Sell exchange not available: {}", strategy.sell_exchange));
        }
        
        Ok(())
    }
    
    async fn execute_real_arbitrage(&self, strategy: &ArbitrageStrategy) -> Result<ExecutionResult> {
        let execution_id = Uuid::new_v4().to_string();
        let start_time = std::time::Instant::now();
        
        info!("💰 Executing REAL arbitrage: {}", execution_id);
        info!("   Buy: {} on {} @ ${:.6}", strategy.symbol, strategy.buy_exchange, strategy.buy_price);
        info!("   Sell: {} on {} @ ${:.6}", strategy.symbol, strategy.sell_exchange, strategy.sell_price);
        info!("   Position: ${:.0}", strategy.position_size_usd);
        
        // Step 1: Place buy order
        let buy_client = self.exchange_clients.get(&strategy.buy_exchange)
            .ok_or_else(|| anyhow::anyhow!("Buy exchange not found"))?;
        
        let buy_order = OrderRequest {
            symbol: strategy.symbol.clone(),
            side: OrderSide::Buy,
            order_type: OrderType::Market,
            quantity: strategy.quantity,
            price: Some(strategy.buy_price),
            time_in_force: TimeInForce::IOC,
        };
        
        let buy_result = buy_client.place_order(buy_order).await?;
        
        // Step 2: Wait for buy fill
        let filled_buy = self.wait_for_fill(&**buy_client, &buy_result.order_id, 30).await?;
        
        if filled_buy.status != OrderStatus::Filled {
            return Err(anyhow::anyhow!("Buy order not filled: {:?}", filled_buy.status));
        }
        
        // Step 3: Place sell order
        let sell_client = self.exchange_clients.get(&strategy.sell_exchange)
            .ok_or_else(|| anyhow::anyhow!("Sell exchange not found"))?;
        
        let sell_order = OrderRequest {
            symbol: strategy.symbol.clone(),
            side: OrderSide::Sell,
            order_type: OrderType::Market,
            quantity: filled_buy.filled_quantity,
            price: Some(strategy.sell_price),
            time_in_force: TimeInForce::IOC,
        };
        
        let sell_result = sell_client.place_order(sell_order).await?;
        let filled_sell = self.wait_for_fill(&**sell_client, &sell_result.order_id, 30).await?;
        
        // Calculate P&L
        let gross_profit = (filled_sell.average_price - filled_buy.average_price) * filled_buy.filled_quantity;
        let total_fees = filled_buy.commission + filled_sell.commission;
        let net_profit = gross_profit - total_fees;
        
        // Update metrics
        self.metrics.total_orders.fetch_add(2, std::sync::atomic::Ordering::Relaxed);
        if filled_sell.status == OrderStatus::Filled {
            self.metrics.successful_orders.fetch_add(2, std::sync::atomic::Ordering::Relaxed);
        }
        self.metrics.total_volume.fetch_add((strategy.position_size_usd * 100.0) as u64, std::sync::atomic::Ordering::Relaxed);
        self.metrics.total_profit.fetch_add((net_profit * 100.0) as i64, std::sync::atomic::Ordering::Relaxed);
        
        // Update portfolio
        self.portfolio_manager.record_trade(&filled_buy, &filled_sell).await?;
        
        let result = ExecutionResult {
            execution_id,
            strategy_id: strategy.id.clone(),
            success: filled_sell.status == OrderStatus::Filled,
            gross_profit_usd: gross_profit,
            net_profit_usd: net_profit,
            total_fees_usd: total_fees,
            execution_time_ms: start_time.elapsed().as_millis() as u64,
            buy_fill: filled_buy,
            sell_fill: filled_sell,
        };
        
        if result.success {
            info!("✅ Arbitrage completed: ${:.2} net profit", net_profit);
        } else {
            error!("❌ Arbitrage failed");
        }
        
        Ok(result)
    }
    
    async fn execute_paper_arbitrage(&self, strategy: &ArbitrageStrategy) -> Result<ExecutionResult> {
        info!("📝 Executing PAPER arbitrage: {}", strategy.id);
        
        // Simulate execution with realistic timing
        tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
        
        let simulated_slippage = 0.0005; // 0.05%
        let actual_buy_price = strategy.buy_price * (1.0 + simulated_slippage);
        let actual_sell_price = strategy.sell_price * (1.0 - simulated_slippage);
        
        let gross_profit = (actual_sell_price - actual_buy_price) * strategy.quantity;
        let estimated_fees = strategy.position_size_usd * 0.002; // 0.2% total fees
        let net_profit = gross_profit - estimated_fees;
        
        Ok(ExecutionResult {
            execution_id: Uuid::new_v4().to_string(),
            strategy_id: strategy.id.clone(),
            success: net_profit > 0.0,
            gross_profit_usd: gross_profit,
            net_profit_usd: net_profit,
            total_fees_usd: estimated_fees,
            execution_time_ms: 500,
            buy_fill: OrderFill::simulated(strategy, actual_buy_price, OrderSide::Buy),
            sell_fill: OrderFill::simulated(strategy, actual_sell_price, OrderSide::Sell),
        })
    }
    
    async fn wait_for_fill(&self, client: &dyn AuthenticatedExchange, order_id: &str, timeout_seconds: u64) -> Result<OrderFill> {
        let start = std::time::Instant::now();
        
        while start.elapsed().as_secs() < timeout_seconds {
            let status = client.get_order_status(order_id).await?;
            
            match status.status {
                OrderStatus::Filled => return Ok(status),
                OrderStatus::Failed | OrderStatus::Cancelled => {
                    return Err(anyhow::anyhow!("Order failed: {:?}", status.status));
                }
                _ => {
                    tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
                }
            }
        }
        
        Err(anyhow::anyhow!("Order timeout after {} seconds", timeout_seconds))
    }
    
    pub async fn get_trading_metrics(&self) -> TradingMetricsSnapshot {
        TradingMetricsSnapshot {
            total_orders: self.metrics.total_orders.load(std::sync::atomic::Ordering::Relaxed),
            successful_orders: self.metrics.successful_orders.load(std::sync::atomic::Ordering::Relaxed),
            total_volume_usd: self.metrics.total_volume.load(std::sync::atomic::Ordering::Relaxed) as f64 / 100.0,
            total_profit_usd: self.metrics.total_profit.load(std::sync::atomic::Ordering::Relaxed) as f64 / 100.0,
        }
    }
    
    pub async fn emergency_stop(&self) -> Result<()> {
        error!("🚨 EMERGENCY STOP ACTIVATED");
        
        // Cancel all pending orders
        for exchange_entry in self.exchange_clients.iter() {
            if let Err(e) = exchange_entry.value().cancel_all_orders().await {
                error!("Failed to cancel orders on {}: {}", exchange_entry.key(), e);
            }
        }
        
        // Update config
        // self.config.emergency_stop = true; // Would need interior mutability
        
        error!("🛑 Emergency stop completed");
        Ok(())
    }
}

#[derive(Debug, Clone)]
pub struct ArbitrageStrategy {
    pub id: String,
    pub symbol: String,
    pub buy_exchange: String,
    pub sell_exchange: String,
    pub buy_price: f64,
    pub sell_price: f64,
    pub quantity: f64,
    pub position_size_usd: f64,
    pub expected_profit_usd: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct ExecutionResult {
    pub execution_id: String,
    pub strategy_id: String,
    pub success: bool,
    pub gross_profit_usd: f64,
    pub net_profit_usd: f64,
    pub total_fees_usd: f64,
    pub execution_time_ms: u64,
    pub buy_fill: OrderFill,
    pub sell_fill: OrderFill,
}

#[derive(Debug, Serialize)]
pub struct TradingMetricsSnapshot {
    pub total_orders: u64,
    pub successful_orders: u64,
    pub total_volume_usd: f64,
    pub total_profit_usd: f64,
}

pub struct OrderManager {
    active_orders: Arc<RwLock<HashMap<String, OrderFill>>>,
}

impl OrderManager {
    pub fn new() -> Self {
        Self {
            active_orders: Arc::new(RwLock::new(HashMap::new())),
        }
    }
}
