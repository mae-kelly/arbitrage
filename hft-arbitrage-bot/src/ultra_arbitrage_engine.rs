//! Ultra-High Performance Arbitrage Engine
//! Designed for educational simulation of institutional-grade systems

use anyhow::Result;
use dashmap::DashMap;
use parking_lot::RwLock;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::Semaphore;
use tracing::{info, warn, debug, error};
use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Serialize)]
pub struct UltraOpportunity {
    pub id: u64,
    pub symbol: String,
    pub buy_exchange: String,
    pub sell_exchange: String,
    pub buy_price: f64,
    pub sell_price: f64,
    pub volume_available: f64,
    pub gross_profit_usd: f64,
    pub net_profit_usd: f64,
    pub profit_percentage: f64,
    pub execution_time_estimate_ms: u64,
    pub confidence_score: f64,
    pub risk_score: f64,
    pub flash_loan_optimal: bool,
    pub flash_loan_provider: String,
    pub flash_loan_cost: f64,
    pub gas_cost_estimate: f64,
    pub slippage_estimate: f64,
    pub market_impact: f64,
    pub liquidity_score: f64,
    pub urgency_level: UrgencyLevel,
    pub estimated_roi_annualized: f64,
    pub capital_efficiency: f64,
}

#[derive(Debug, Clone, Serialize)]
pub enum UrgencyLevel {
    Critical,    // Execute immediately (>2% profit)
    High,        // Execute within 1 second (>1% profit)
    Medium,      // Execute within 5 seconds (>0.5% profit)
    Low,         // Execute within 30 seconds (>0.1% profit)
}

pub struct UltraArbitrageEngine {
    // Lock-free concurrent data structures for maximum performance
    live_prices: Arc<DashMap<String, PricePoint>>,
    opportunities: Arc<DashMap<u64, UltraOpportunity>>,
    execution_queue: Arc<RwLock<Vec<UltraOpportunity>>>,
    
    // Performance tracking
    scan_count: Arc<std::sync::atomic::AtomicU64>,
    total_profit_simulated: Arc<std::sync::atomic::AtomicU64>, // in cents
    execution_times: Arc<RwLock<Vec<u64>>>,
    
    // Rate limiting and concurrency control
    api_semaphore: Arc<Semaphore>,
    max_concurrent_scans: usize,
    scan_interval_ms: u64,
    
    // Market data sources
    exchange_weights: DashMap<String, f64>, // Quality/reliability scores
    symbol_priorities: DashMap<String, f64>, // Volume-based priorities
}

#[derive(Debug, Clone)]
struct PricePoint {
    price: f64,
    bid: f64,
    ask: f64,
    volume_24h: f64,
    liquidity_depth: f64,
    last_update: Instant,
    exchange: String,
    symbol: String,
}

impl UltraArbitrageEngine {
    pub fn new() -> Self {
        Self {
            live_prices: Arc::new(DashMap::with_capacity(50000)),
            opportunities: Arc::new(DashMap::with_capacity(10000)),
            execution_queue: Arc::new(RwLock::new(Vec::with_capacity(1000))),
            scan_count: Arc::new(std::sync::atomic::AtomicU64::new(0)),
            total_profit_simulated: Arc::new(std::sync::atomic::AtomicU64::new(0)),
            execution_times: Arc::new(RwLock::new(Vec::with_capacity(10000))),
            api_semaphore: Arc::new(Semaphore::new(500)), // 500 concurrent requests
            max_concurrent_scans: 100,
            scan_interval_ms: 100, // 100ms between scans for ultra-high frequency
            exchange_weights: DashMap::new(),
            symbol_priorities: DashMap::new(),
        }
    }

    pub async fn initialize_ultra_mode(&self) -> Result<()> {
        info!("🚀 Initializing Ultra-High Performance Mode");
        
        // Initialize exchange reliability weights
        self.initialize_exchange_weights();
        
        // Initialize symbol priorities based on volume
        self.initialize_symbol_priorities().await?;
        
        info!("✅ Ultra mode initialized - Target: 10,000+ scans/minute");
        Ok(())
    }

    fn initialize_exchange_weights(&self) {
        // Weight exchanges by reliability, liquidity, and API quality
        self.exchange_weights.insert("coinbase".to_string(), 0.95);
        self.exchange_weights.insert("kraken".to_string(), 0.93);
        self.exchange_weights.insert("binance".to_string(), 0.97); // If available
        self.exchange_weights.insert("kucoin".to_string(), 0.85);
        self.exchange_weights.insert("gate_io".to_string(), 0.80);
        self.exchange_weights.insert("mexc".to_string(), 0.75);
        
        // DEX weights (higher gas but often better prices)
        self.exchange_weights.insert("uniswap_v3".to_string(), 0.88);
        self.exchange_weights.insert("sushiswap".to_string(), 0.82);
        self.exchange_weights.insert("curve".to_string(), 0.85);
    }

    async fn initialize_symbol_priorities(&self) -> Result<()> {
        // Priority based on 24h volume and volatility
        let high_priority_symbols = vec![
            ("BTC-USD", 1.0),
            ("ETH-USD", 0.95),
            ("BNB-USD", 0.85),
            ("ADA-USD", 0.75),
            ("SOL-USD", 0.80),
            ("MATIC-USD", 0.70),
            ("LINK-USD", 0.65),
            ("UNI-USD", 0.60),
            ("AAVE-USD", 0.55),
            ("MKR-USD", 0.50),
        ];

        for (symbol, priority) in high_priority_symbols {
            self.symbol_priorities.insert(symbol.to_string(), priority);
        }

        Ok(())
    }

    pub async fn ultra_scan_cycle(&self) -> Result<Vec<UltraOpportunity>> {
        let scan_start = Instant::now();
        let scan_id = self.scan_count.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        
        debug!("🔍 Ultra scan #{} starting", scan_id);

        // Multi-threaded opportunity detection across all price pairs
        let opportunities = self.detect_ultra_opportunities().await?;
        
        // Advanced filtering and optimization
        let optimized_opportunities = self.optimize_opportunities(opportunities).await?;
        
        // Update execution queue with best opportunities
        self.update_execution_queue(optimized_opportunities.clone()).await;
        
        let scan_time = scan_start.elapsed();
        self.execution_times.write().push(scan_time.as_micros() as u64);
        
        if scan_time.as_millis() > 50 {
            warn!("⚠️  Slow scan #{}: {}ms (target: <50ms)", scan_id, scan_time.as_millis());
        } else {
            debug!("⚡ Ultra scan #{} completed in {}μs", scan_id, scan_time.as_micros());
        }

        Ok(optimized_opportunities)
    }

    async fn detect_ultra_opportunities(&self) -> Result<Vec<UltraOpportunity>> {
        let mut opportunities = Vec::new();
        let mut opportunity_id = 0u64;

        // Parallel opportunity detection across all symbol pairs
        for symbol_entry in self.symbol_priorities.iter() {
            let symbol = symbol_entry.key();
            let priority = *symbol_entry.value();
            
            // Skip low priority symbols if system is under load
            if priority < 0.5 && opportunities.len() > 1000 {
                continue;
            }

            // Find all exchanges trading this symbol
            let symbol_prices: Vec<_> = self.live_prices
                .iter()
                .filter(|entry| entry.key().contains(symbol))
                .collect();

            // Compare all exchange pairs for this symbol
            for i in 0..symbol_prices.len() {
                for j in (i + 1)..symbol_prices.len() {
                    if let Some(opportunity) = self.analyze_pair(
                        &symbol_prices[i], 
                        &symbol_prices[j], 
                        opportunity_id,
                        priority
                    ).await {
                        opportunities.push(opportunity);
                        opportunity_id += 1;
                    }
                }
            }
        }

        // Sort by profit potential
        opportunities.sort_by(|a, b| b.net_profit_usd.partial_cmp(&a.net_profit_usd).unwrap());
        
        Ok(opportunities.into_iter().take(100).collect()) // Top 100 opportunities
    }

    async fn analyze_pair(
        &self,
        price1: &dashmap::mapref::one::Ref<String, PricePoint>,
        price2: &dashmap::mapref::one::Ref<String, PricePoint>,
        opportunity_id: u64,
        symbol_priority: f64,
    ) -> Option<UltraOpportunity> {
        let p1 = price1.value();
        let p2 = price2.value();

        // Quick profitability check
        let profit_check = if p1.ask < p2.bid {
            (p2.bid - p1.ask) / p1.ask
        } else if p2.ask < p1.bid {
            (p1.bid - p2.ask) / p2.ask
        } else {
            return None; // No arbitrage opportunity
        };

        if profit_check < 0.001 { // Less than 0.1% gross profit
            return None;
        }

        // Determine trade direction and calculate detailed metrics
        let (buy_exchange, sell_exchange, buy_price, sell_price) = if p1.ask < p2.bid {
            (p1.exchange.clone(), p2.exchange.clone(), p1.ask, p2.bid)
        } else {
            (p2.exchange.clone(), p1.exchange.clone(), p2.ask, p1.bid)
        };

        // Advanced calculations
        let trade_size = self.calculate_optimal_trade_size(p1, p2, symbol_priority);
        let gross_profit = (sell_price - buy_price) * trade_size;
        
        // Cost calculations
        let trading_fees = self.estimate_trading_fees(&buy_exchange, &sell_exchange, trade_size);
        let gas_costs = self.estimate_gas_costs(&buy_exchange, &sell_exchange).await;
        let slippage = self.estimate_slippage(p1, p2, trade_size);
        
        let total_costs = trading_fees + gas_costs + slippage;
        let net_profit = gross_profit - total_costs;

        if net_profit < 10.0 { // Minimum $10 profit after all costs
            return None;
        }

        // Flash loan optimization
        let (flash_loan_optimal, flash_loan_provider, flash_loan_cost) = 
            self.optimize_flash_loan(trade_size, net_profit).await;

        // Risk and confidence scoring
        let confidence_score = self.calculate_confidence_score(p1, p2, symbol_priority);
        let risk_score = self.calculate_risk_score(p1, p2, trade_size);
        
        // Urgency classification
        let urgency_level = match profit_check {
            x if x > 0.02 => UrgencyLevel::Critical,
            x if x > 0.01 => UrgencyLevel::High,
            x if x > 0.005 => UrgencyLevel::Medium,
            _ => UrgencyLevel::Low,
        };

        Some(UltraOpportunity {
            id: opportunity_id,
            symbol: p1.symbol.clone(),
            buy_exchange,
            sell_exchange,
            buy_price,
            sell_price,
            volume_available: trade_size,
            gross_profit_usd: gross_profit,
            net_profit_usd: net_profit,
            profit_percentage: profit_check * 100.0,
            execution_time_estimate_ms: self.estimate_execution_time(p1, p2),
            confidence_score,
            risk_score,
            flash_loan_optimal,
            flash_loan_provider,
            flash_loan_cost,
            gas_cost_estimate: gas_costs,
            slippage_estimate: slippage,
            market_impact: self.calculate_market_impact(p1, p2, trade_size),
            liquidity_score: (p1.liquidity_depth + p2.liquidity_depth) / 2.0,
            urgency_level,
            estimated_roi_annualized: (profit_check * 365.0 * 24.0 * 60.0) * 100.0, // Assuming 1 trade per minute
            capital_efficiency: net_profit / trade_size,
        })
    }

    fn calculate_optimal_trade_size(&self, p1: &PricePoint, p2: &PricePoint, priority: f64) -> f64 {
        // Base trade size adjusted by liquidity and priority
        let base_size = 10000.0; // $10k base
        let liquidity_factor = (p1.liquidity_depth.min(p2.liquidity_depth) / 100000.0).min(2.0);
        let priority_factor = priority;
        
        base_size * liquidity_factor * priority_factor
    }

    fn estimate_trading_fees(&self, buy_exchange: &str, sell_exchange: &str, trade_size: f64) -> f64 {
        // Conservative fee estimates
        let buy_fee_rate = match buy_exchange {
            "coinbase" => 0.006, // 0.6%
            "kraken" => 0.0026,  // 0.26%
            "kucoin" => 0.001,   // 0.1%
            _ => 0.0025,         // 0.25% default
        };
        
        let sell_fee_rate = match sell_exchange {
            "coinbase" => 0.006,
            "kraken" => 0.0026,
            "kucoin" => 0.001,
            _ => 0.0025,
        };
        
        trade_size * (buy_fee_rate + sell_fee_rate)
    }

    async fn estimate_gas_costs(&self, buy_exchange: &str, sell_exchange: &str) -> f64 {
        // DEX transactions require gas
        let is_dex_trade = matches!(buy_exchange, "uniswap_v3" | "sushiswap" | "curve") ||
                          matches!(sell_exchange, "uniswap_v3" | "sushiswap" | "curve");
        
        if is_dex_trade {
            // Estimate current gas costs (this would connect to real gas price APIs)
            50.0 // $50 estimated gas cost
        } else {
            0.0
        }
    }

    fn estimate_slippage(&self, p1: &PricePoint, p2: &PricePoint, trade_size: f64) -> f64 {
        let avg_liquidity = (p1.liquidity_depth + p2.liquidity_depth) / 2.0;
        let liquidity_ratio = trade_size / avg_liquidity.max(1000.0);
        
        // Slippage increases non-linearly with trade size relative to liquidity
        let slippage_rate = if liquidity_ratio > 0.1 {
            0.005 // 0.5% slippage for large trades
        } else {
            liquidity_ratio * 0.01 // Linear up to 0.1 ratio
        };
        
        trade_size * slippage_rate
    }

    async fn optimize_flash_loan(&self, trade_size: f64, net_profit: f64) -> (bool, String, f64) {
        if net_profit < 50.0 { // Minimum profit for flash loan viability
            return (false, "none".to_string(), 0.0);
        }

        // Compare flash loan providers
        let aave_cost = trade_size * 0.0005; // 0.05%
        let dydx_cost = 0.0; // Free
        let balancer_cost = 0.0; // Free
        
        let gas_overhead = 25.0; // Additional gas for flash loan
        
        if dydx_cost + gas_overhead < aave_cost {
            (true, "dydx".to_string(), dydx_cost + gas_overhead)
        } else if balancer_cost + gas_overhead < aave_cost {
            (true, "balancer".to_string(), balancer_cost + gas_overhead)
        } else if net_profit > aave_cost + gas_overhead + 25.0 {
            (true, "aave".to_string(), aave_cost + gas_overhead)
        } else {
            (false, "none".to_string(), 0.0)
        }
    }

    fn calculate_confidence_score(&self, p1: &PricePoint, p2: &PricePoint, priority: f64) -> f64 {
        let exchange1_weight = self.exchange_weights.get(&p1.exchange).map(|w| *w.value()).unwrap_or(0.5);
        let exchange2_weight = self.exchange_weights.get(&p2.exchange).map(|w| *w.value()).unwrap_or(0.5);
        
        let data_freshness = {
            let age1 = p1.last_update.elapsed().as_secs_f64();
            let age2 = p2.last_update.elapsed().as_secs_f64();
            let max_age = age1.max(age2);
            (10.0 - max_age).max(0.0) / 10.0 // Decay over 10 seconds
        };
        
        let liquidity_factor = (p1.liquidity_depth.min(p2.liquidity_depth) / 50000.0).min(1.0);
        
        (exchange1_weight + exchange2_weight) / 2.0 * data_freshness * liquidity_factor * priority
    }

    fn calculate_risk_score(&self, p1: &PricePoint, p2: &PricePoint, trade_size: f64) -> f64 {
        let liquidity_risk = if p1.liquidity_depth < trade_size || p2.liquidity_depth < trade_size {
            0.8 // High risk if trade size exceeds liquidity
        } else {
            0.2
        };
        
        let volatility_risk = {
            // Estimate volatility from bid-ask spread
            let spread1 = (p1.ask - p1.bid) / p1.price;
            let spread2 = (p2.ask - p2.bid) / p2.price;
            ((spread1 + spread2) / 2.0 * 100.0).min(0.5) // Cap at 50% risk
        };
        
        let execution_risk = 0.1; // Base execution risk
        
        (liquidity_risk + volatility_risk + execution_risk) / 3.0
    }

    fn estimate_execution_time(&self, p1: &PricePoint, p2: &PricePoint) -> u64 {
        // Estimate based on exchange types
        let base_time = 200; // 200ms base
        
        let is_dex1 = matches!(p1.exchange.as_str(), "uniswap_v3" | "sushiswap" | "curve");
        let is_dex2 = matches!(p2.exchange.as_str(), "uniswap_v3" | "sushiswap" | "curve");
        
        if is_dex1 || is_dex2 {
            base_time + 5000 // Add 5 seconds for DEX confirmation times
        } else {
            base_time + 1000 // Add 1 second for CEX execution
        }
    }

    fn calculate_market_impact(&self, p1: &PricePoint, p2: &PricePoint, trade_size: f64) -> f64 {
        let avg_liquidity = (p1.liquidity_depth + p2.liquidity_depth) / 2.0;
        trade_size / avg_liquidity.max(1.0)
    }

    async fn optimize_opportunities(&self, mut opportunities: Vec<UltraOpportunity>) -> Result<Vec<UltraOpportunity>> {
        // Advanced optimization algorithms
        
        // 1. Remove conflicting opportunities (same symbol, overlapping exchanges)
        opportunities = self.remove_conflicts(opportunities);
        
        // 2. Optimize for capital efficiency
        opportunities = self.optimize_capital_efficiency(opportunities);
        
        // 3. Sort by risk-adjusted returns
        opportunities.sort_by(|a, b| {
            let score_a = a.net_profit_usd / (a.risk_score + 0.1);
            let score_b = b.net_profit_usd / (b.risk_score + 0.1);
            score_b.partial_cmp(&score_a).unwrap()
        });
        
        Ok(opportunities.into_iter().take(50).collect()) // Top 50 optimized opportunities
    }

    fn remove_conflicts(&self, opportunities: Vec<UltraOpportunity>) -> Vec<UltraOpportunity> {
        let mut result = Vec::new();
        let mut used_exchanges: std::collections::HashSet<String> = std::collections::HashSet::new();
        
        for opp in opportunities {
            if !used_exchanges.contains(&opp.buy_exchange) && !used_exchanges.contains(&opp.sell_exchange) {
                used_exchanges.insert(opp.buy_exchange.clone());
                used_exchanges.insert(opp.sell_exchange.clone());
                result.push(opp);
            }
        }
        
        result
    }

    fn optimize_capital_efficiency(&self, opportunities: Vec<UltraOpportunity>) -> Vec<UltraOpportunity> {
        // Prioritize opportunities that maximize profit per dollar of capital
        let mut optimized = opportunities;
        optimized.sort_by(|a, b| b.capital_efficiency.partial_cmp(&a.capital_efficiency).unwrap());
        optimized
    }

    async fn update_execution_queue(&self, opportunities: Vec<UltraOpportunity>) {
        let mut queue = self.execution_queue.write();
        queue.clear();
        
        // Add critical and high urgency opportunities to execution queue
        for opp in opportunities {
            match opp.urgency_level {
                UrgencyLevel::Critical | UrgencyLevel::High => {
                    queue.push(opp);
                }
                _ => {} // Lower urgency opportunities not queued for immediate execution
            }
        }
        
        // Sort execution queue by profit potential
        queue.sort_by(|a, b| b.net_profit_usd.partial_cmp(&a.net_profit_usd).unwrap());
    }

    pub async fn get_performance_stats(&self) -> PerformanceStats {
        let execution_times = self.execution_times.read();
        let total_scans = self.scan_count.load(std::sync::atomic::Ordering::Relaxed);
        let total_profit = self.total_profit_simulated.load(std::sync::atomic::Ordering::Relaxed) as f64 / 100.0;
        
        let avg_execution_time = if execution_times.is_empty() {
            0
        } else {
            execution_times.iter().sum::<u64>() / execution_times.len() as u64
        };
        
        let scans_per_second = if avg_execution_time > 0 {
            1_000_000 / avg_execution_time // Convert from microseconds
        } else {
            0
        };

        PerformanceStats {
            total_scans,
            total_simulated_profit: total_profit,
            avg_scan_time_us: avg_execution_time,
            scans_per_second,
            opportunities_in_queue: self.execution_queue.read().len() as u64,
            active_price_feeds: self.live_prices.len() as u64,
        }
    }
}

#[derive(Debug, Serialize)]
pub struct PerformanceStats {
    pub total_scans: u64,
    pub total_simulated_profit: f64,
    pub avg_scan_time_us: u64,
    pub scans_per_second: u64,
    pub opportunities_in_queue: u64,
    pub active_price_feeds: u64,
}
