//! Realistic Execution Simulator using REAL market data
//! Simulates trade execution using actual live prices and market conditions

use super::live_data_fetcher::{LiveMarketData, LiveGasData, ArbitrageOpportunity};
use anyhow::Result;
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::time::{Duration, Instant};
use rand::Rng;
use tracing::{info, warn, debug};

#[derive(Debug, Clone, Serialize)]
pub struct RealisticExecutionResult {
    pub opportunity_id: String,
    pub success: bool,
    pub strategy_type: String,
    
    // Financial results based on REAL market data
    pub gross_profit_usd: f64,
    pub net_profit_usd: f64,
    pub total_fees_usd: f64,
    pub gas_cost_usd: f64,
    pub slippage_cost_usd: f64,
    pub mev_impact_usd: f64,
    
    // Execution details
    pub execution_time_ms: u64,
    pub actual_buy_price: f64,
    pub actual_sell_price: f64,
    pub expected_buy_price: f64,
    pub expected_sell_price: f64,
    pub trade_size_usd: f64,
    
    // Market conditions at execution
    pub market_conditions: ExecutionMarketConditions,
    pub failure_reason: Option<String>,
    
    // Real exchange data
    pub buy_venue_data: VenueExecutionData,
    pub sell_venue_data: VenueExecutionData,
}

#[derive(Debug, Clone, Serialize)]
pub struct ExecutionMarketConditions {
    pub eth_gas_price_gwei: f64,
    pub network_congestion: f64,
    pub market_volatility_estimate: f64,
    pub overall_liquidity_score: f64,
    pub timestamp: u64,
}

#[derive(Debug, Clone, Serialize)]
pub struct VenueExecutionData {
    pub venue: String,
    pub symbol: String,
    pub order_book_liquidity: f64,
    pub spread_bps: f64,
    pub executed_price: f64,
    pub slippage_bps: f64,
    pub trading_fee_bps: f64,
    pub execution_latency_ms: u64,
}

pub struct RealPriceExecutionSimulator {
    // Real exchange fee data
    exchange_fees: HashMap<String, ExchangeFeeStructure>,
    
    // Performance tracking
    execution_history: Vec<RealisticExecutionResult>,
    total_simulated_volume: f64,
    total_simulated_profit: f64,
}

#[derive(Debug, Clone)]
struct ExchangeFeeStructure {
    maker_fee_bps: f64,
    taker_fee_bps: f64,
    withdrawal_fee_usd: f64,
    min_fee_usd: f64,
}

impl RealPriceExecutionSimulator {
    pub fn new() -> Self {
        Self {
            exchange_fees: Self::initialize_real_exchange_fees(),
            execution_history: Vec::new(),
            total_simulated_volume: 0.0,
            total_simulated_profit: 0.0,
        }
    }

    fn initialize_real_exchange_fees() -> HashMap<String, ExchangeFeeStructure> {
        let mut fees = HashMap::new();
        
        // REAL exchange fees as of 2024/2025
        fees.insert("binance".to_string(), ExchangeFeeStructure {
            maker_fee_bps: 10.0,  // 0.1%
            taker_fee_bps: 10.0,  // 0.1%
            withdrawal_fee_usd: 1.0,
            min_fee_usd: 0.10,
        });
        
        fees.insert("coinbase".to_string(), ExchangeFeeStructure {
            maker_fee_bps: 50.0,  // 0.5%
            taker_fee_bps: 60.0,  // 0.6%
            withdrawal_fee_usd: 2.0,
            min_fee_usd: 0.99,
        });
        
        fees.insert("kraken".to_string(), ExchangeFeeStructure {
            maker_fee_bps: 16.0,  // 0.16%
            taker_fee_bps: 26.0,  // 0.26%
            withdrawal_fee_usd: 1.5,
            min_fee_usd: 0.25,
        });
        
        fees.insert("uniswap_v3".to_string(), ExchangeFeeStructure {
            maker_fee_bps: 30.0,  // 0.3% (typical pool)
            taker_fee_bps: 30.0,  // Same for AMM
            withdrawal_fee_usd: 0.0,
            min_fee_usd: 0.0,
        });
        
        fees
    }

    pub async fn simulate_arbitrage_execution(
        &mut self,
        opportunity: &ArbitrageOpportunity,
        current_prices: &HashMap<String, LiveMarketData>,
        gas_data: &HashMap<String, LiveGasData>,
        trade_size_usd: f64,
    ) -> Result<RealisticExecutionResult> {
        let execution_start = Instant::now();
        let opportunity_id = format!("arb_{}", uuid::Uuid::new_v4());
        
        info!("🎭 Simulating REAL arbitrage execution:");
        info!("   Symbol: {}", opportunity.symbol);
        info!("   Buy: {} @ ${:.6}", opportunity.buy_venue, opportunity.buy_price);
        info!("   Sell: {} @ ${:.6}", opportunity.sell_venue, opportunity.sell_price);
        info!("   Expected profit: {:.3}%", opportunity.profit_percentage);
        info!("   Trade size: ${:.0}", trade_size_usd);

        // Get current REAL market data for both venues
        let buy_venue_key = format!("{}:{}", opportunity.buy_venue, opportunity.symbol);
        let sell_venue_key = format!("{}:{}", opportunity.sell_venue, opportunity.symbol);
        
        let buy_venue_data = current_prices.get(&buy_venue_key)
            .ok_or_else(|| anyhow::anyhow!("No current price data for buy venue: {}", buy_venue_key))?;
        
        let sell_venue_data = current_prices.get(&sell_venue_key)
            .ok_or_else(|| anyhow::anyhow!("No current price data for sell venue: {}", sell_venue_key))?;

        // Check if opportunity still exists with current REAL prices
        let current_profit_pct = ((sell_venue_data.bid - buy_venue_data.ask) / buy_venue_data.ask) * 100.0;
        
        if current_profit_pct < 0.05 {
            return Ok(RealisticExecutionResult {
                opportunity_id,
                success: false,
                strategy_type: "cross_venue_arbitrage".to_string(),
                gross_profit_usd: 0.0,
                net_profit_usd: 0.0,
                total_fees_usd: 0.0,
                gas_cost_usd: 0.0,
                slippage_cost_usd: 0.0,
                mev_impact_usd: 0.0,
                execution_time_ms: execution_start.elapsed().as_millis() as u64,
                actual_buy_price: buy_venue_data.ask,
                actual_sell_price: sell_venue_data.bid,
                expected_buy_price: opportunity.buy_price,
                expected_sell_price: opportunity.sell_price,
                trade_size_usd,
                market_conditions: self.get_current_market_conditions(gas_data),
                failure_reason: Some("Opportunity disappeared - prices moved".to_string()),
                buy_venue_data: VenueExecutionData {
                    venue: opportunity.buy_venue.clone(),
                    symbol: opportunity.symbol.clone(),
                    order_book_liquidity: buy_venue_data.order_book_depth.total_ask_liquidity,
                    spread_bps: buy_venue_data.spread_bps,
                    executed_price: buy_venue_data.ask,
                    slippage_bps: 0.0,
                    trading_fee_bps: 0.0,
                    execution_latency_ms: 0,
                },
                sell_venue_data: VenueExecutionData {
                    venue: opportunity.sell_venue.clone(),
                    symbol: opportunity.symbol.clone(),
                    order_book_liquidity: sell_venue_data.order_book_depth.total_bid_liquidity,
                    spread_bps: sell_venue_data.spread_bps,
                    executed_price: sell_venue_data.bid,
                    slippage_bps: 0.0,
                    trading_fee_bps: 0.0,
                    execution_latency_ms: 0,
                },
            });
        }

        // Calculate trade size based on REAL liquidity constraints
        let max_buy_size = buy_venue_data.order_book_depth.total_ask_liquidity;
        let max_sell_size = sell_venue_data.order_book_depth.total_bid_liquidity;
        let liquidity_constrained_size = trade_size_usd.min(max_buy_size).min(max_sell_size);
        
        if liquidity_constrained_size < trade_size_usd * 0.5 {
            warn!("Insufficient liquidity: wanted ${:.0}, available ${:.0}", trade_size_usd, liquidity_constrained_size);
        }

        // Simulate execution with REAL market impact
        let buy_execution = self.simulate_venue_execution(
            buy_venue_data,
            liquidity_constrained_size,
            true, // is_buy
            gas_data,
        ).await?;

        let sell_execution = self.simulate_venue_execution(
            sell_venue_data,
            liquidity_constrained_size,
            false, // is_sell
            gas_data,
        ).await?;

        // Calculate realistic MEV impact
        let mev_impact = self.calculate_mev_impact(
            &opportunity.symbol,
            current_profit_pct,
            liquidity_constrained_size,
        );

        // Calculate final results
        let quantity = liquidity_constrained_size / buy_execution.executed_price;
        let gross_profit = (sell_execution.executed_price - buy_execution.executed_price) * quantity;
        let total_fees = buy_execution.trading_fee_bps / 10000.0 * liquidity_constrained_size +
                        sell_execution.trading_fee_bps / 10000.0 * liquidity_constrained_size;
        let total_gas_cost = buy_execution.gas_cost + sell_execution.gas_cost;
        let total_slippage_cost = (buy_execution.slippage_cost + sell_execution.slippage_cost);
        
        let net_profit = gross_profit - total_fees - total_gas_cost - total_slippage_cost - mev_impact;
        let success = net_profit > 10.0; // Minimum $10 profit

        let execution_time = execution_start.elapsed().as_millis() as u64;

        // Log detailed results
        if success {
            info!("✅ REAL arbitrage simulation successful:");
            info!("   Gross profit: ${:.2}", gross_profit);
            info!("   Trading fees: ${:.2}", total_fees);
            info!("   Gas costs: ${:.2}", total_gas_cost);
            info!("   Slippage: ${:.2}", total_slippage_cost);
            info!("   MEV impact: ${:.2}", mev_impact);
            info!("   NET PROFIT: ${:.2}", net_profit);
            info!("   Execution time: {}ms", execution_time);
        } else {
            warn!("❌ REAL arbitrage simulation failed: ${:.2} net result", net_profit);
        }

        let result = RealisticExecutionResult {
            opportunity_id,
            success,
            strategy_type: "cross_venue_arbitrage".to_string(),
            gross_profit_usd: gross_profit,
            net_profit_usd: net_profit,
            total_fees_usd: total_fees,
            gas_cost_usd: total_gas_cost,
            slippage_cost_usd: total_slippage_cost,
            mev_impact_usd: mev_impact,
            execution_time_ms: execution_time,
            actual_buy_price: buy_execution.executed_price,
            actual_sell_price: sell_execution.executed_price,
            expected_buy_price: opportunity.buy_price,
            expected_sell_price: opportunity.sell_price,
            trade_size_usd: liquidity_constrained_size,
            market_conditions: self.get_current_market_conditions(gas_data),
            failure_reason: if success { None } else { Some("Insufficient profit after costs".to_string()) },
            buy_venue_data: VenueExecutionData {
                venue: opportunity.buy_venue.clone(),
                symbol: opportunity.symbol.clone(),
                order_book_liquidity: buy_venue_data.order_book_depth.total_ask_liquidity,
                spread_bps: buy_venue_data.spread_bps,
                executed_price: buy_execution.executed_price,
                slippage_bps: buy_execution.slippage_bps,
                trading_fee_bps: buy_execution.trading_fee_bps,
                execution_latency_ms: buy_execution.execution_latency_ms,
            },
            sell_venue_data: VenueExecutionData {
                venue: opportunity.sell_venue.clone(),
                symbol: opportunity.symbol.clone(),
                order_book_liquidity: sell_venue_data.order_book_depth.total_bid_liquidity,
                spread_bps: sell_venue_data.spread_bps,
                executed_price: sell_execution.executed_price,
                slippage_bps: sell_execution.slippage_bps,
                trading_fee_bps: sell_execution.trading_fee_bps,
                execution_latency_ms: sell_execution.execution_latency_ms,
            },
        };

        // Update tracking
        self.execution_history.push(result.clone());
        self.total_simulated_volume += liquidity_constrained_size;
        if success {
            self.total_simulated_profit += net_profit;
        }

        Ok(result)
    }

    async fn simulate_venue_execution(
        &self,
        venue_data: &LiveMarketData,
        trade_size_usd: f64,
        is_buy: bool,
        gas_data: &HashMap<String, LiveGasData>,
    ) -> Result<VenueExecution> {
        let mut rng = rand::thread_rng();
        
        // Get fee structure for this venue
        let fee_structure = self.exchange_fees.get(&venue_data.venue)
            .ok_or_else(|| anyhow::anyhow!("Unknown venue: {}", venue_data.venue))?;

        // Calculate realistic slippage based on REAL order book depth
        let base_price = if is_buy { venue_data.ask } else { venue_data.bid };
        let available_liquidity = if is_buy {
            venue_data.order_book_depth.total_ask_liquidity
        } else {
            venue_data.order_book_depth.total_bid_liquidity
        };

        // Slippage calculation based on actual liquidity
        let size_ratio = trade_size_usd / available_liquidity.max(1000.0);
        let base_slippage_bps = venue_data.spread_bps / 2.0; // Half spread as base
        let impact_slippage_bps = size_ratio.sqrt() * 50.0; // Market impact
        let total_slippage_bps = base_slippage_bps + impact_slippage_bps;
        
        // Apply slippage to execution price
        let slippage_multiplier = if is_buy {
            1.0 + (total_slippage_bps / 10000.0)
        } else {
            1.0 - (total_slippage_bps / 10000.0)
        };
        
        let executed_price = base_price * slippage_multiplier;
        let slippage_cost = (executed_price - base_price).abs() * (trade_size_usd / base_price);

        // Calculate trading fees based on REAL fee structure
        let trading_fee_bps = fee_structure.taker_fee_bps; // Assume market orders
        let trading_fee_usd = (trade_size_usd * trading_fee_bps / 10000.0).max(fee_structure.min_fee_usd);

        // Calculate gas costs for DEX venues
        let gas_cost = if self.is_dex_venue(&venue_data.venue) {
            if let Some(eth_gas) = gas_data.get("ethereum") {
                // Estimate gas cost: 150k gas * gas_price * ETH_price
                let gas_units = 150000.0;
                let eth_price = 2500.0; // Approximate ETH price
                (gas_units * eth_gas.fast_gas_gwei / 1e9) * eth_price
            } else {
                50.0 // Fallback estimate
            }
        } else {
            0.0 // CEX don't use gas
        };

        // Simulate execution latency
        let execution_latency_ms = if self.is_dex_venue(&venue_data.venue) {
            // DEX: depends on network
            let base_latency = 12000; // 12s for Ethereum
            let congestion_multiplier = gas_data.get("ethereum")
                .map(|g| 1.0 + g.congestion_level)
                .unwrap_or(1.0);
            (base_latency as f64 * congestion_multiplier) as u64
        } else {
            // CEX: much faster
            50 + rng.gen_range(0..200) // 50-250ms
        };

        Ok(VenueExecution {
            executed_price,
            slippage_bps: total_slippage_bps,
            slippage_cost,
            trading_fee_bps,
            trading_fee_usd,
            gas_cost,
            execution_latency_ms,
        })
    }

    fn calculate_mev_impact(&self, symbol: &str, profit_pct: f64, trade_size: f64) -> f64 {
        let mut rng = rand::thread_rng();
        
        // MEV bots are more likely to target high-profit, high-volume trades
        let mev_target_probability = if profit_pct > 0.5 && trade_size > 50000.0 {
            0.3 // 30% chance for attractive trades
        } else if profit_pct > 0.2 {
            0.15 // 15% chance for medium trades
        } else {
            0.05 // 5% chance for small trades
        };

        if rng.gen::<f64>() < mev_target_probability {
            // MEV impact typically 10-50% of expected profit
            let impact_percentage = 0.1 + rng.gen::<f64>() * 0.4;
            let gross_profit_estimate = (profit_pct / 100.0) * trade_size;
            let mev_impact = gross_profit_estimate * impact_percentage;
            
            debug!("🥪 MEV attack simulated on {}: ${:.2} impact ({:.1}% of profit)", 
                   symbol, mev_impact, impact_percentage * 100.0);
            
            mev_impact
        } else {
            0.0
        }
    }

    fn get_current_market_conditions(&self, gas_data: &HashMap<String, LiveGasData>) -> ExecutionMarketConditions {
        let eth_gas = gas_data.get("ethereum");
        
        ExecutionMarketConditions {
            eth_gas_price_gwei: eth_gas.map(|g| g.fast_gas_gwei).unwrap_or(30.0),
            network_congestion: eth_gas.map(|g| g.congestion_level).unwrap_or(0.5),
            market_volatility_estimate: 0.3 + rand::random::<f64>() * 0.4, // 30-70%
            overall_liquidity_score: 0.7 + rand::random::<f64>() * 0.3, // 70-100%
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        }
    }

    fn is_dex_venue(&self, venue: &str) -> bool {
        matches!(venue, "uniswap_v3" | "curve" | "balancer" | "pancakeswap" | "sushiswap")
    }

    pub fn get_simulation_statistics(&self) -> SimulationStatistics {
        let total_executions = self.execution_history.len();
        let successful_executions = self.execution_history.iter().filter(|r| r.success).count();
        
        let total_gas_costs: f64 = self.execution_history.iter().map(|r| r.gas_cost_usd).sum();
        let total_fees: f64 = self.execution_history.iter().map(|r| r.total_fees_usd).sum();
        let total_mev_impact: f64 = self.execution_history.iter().map(|r| r.mev_impact_usd).sum();
        
        let avg_execution_time = if total_executions > 0 {
            self.execution_history.iter().map(|r| r.execution_time_ms).sum::<u64>() / total_executions as u64
        } else {
            0
        };

        SimulationStatistics {
            total_simulations: total_executions,
            successful_simulations: successful_executions,
            success_rate: if total_executions > 0 { successful_executions as f64 / total_executions as f64 } else { 0.0 },
            total_simulated_volume_usd: self.total_simulated_volume,
            total_simulated_profit_usd: self.total_simulated_profit,
            total_gas_costs_usd: total_gas_costs,
            total_trading_fees_usd: total_fees,
            total_mev_impact_usd: total_mev_impact,
            average_execution_time_ms: avg_execution_time,
        }
    }
}

#[derive(Debug)]
struct VenueExecution {
    executed_price: f64,
    slippage_bps: f64,
    slippage_cost: f64,
    trading_fee_bps: f64,
    trading_fee_usd: f64,
    gas_cost: f64,
    execution_latency_ms: u64,
}

#[derive(Debug, Serialize)]
pub struct SimulationStatistics {
    pub total_simulations: usize,
    pub successful_simulations: usize,
    pub success_rate: f64,
    pub total_simulated_volume_usd: f64,
    pub total_simulated_profit_usd: f64,
    pub total_gas_costs_usd: f64,
    pub total_trading_fees_usd: f64,
    pub total_mev_impact_usd: f64,
    pub average_execution_time_ms: u64,
}
