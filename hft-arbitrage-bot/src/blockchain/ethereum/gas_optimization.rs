//! Advanced gas optimization strategies

use ethers::prelude::*;
use anyhow::Result;
use std::collections::VecDeque;

pub struct GasOptimizer {
    gas_price_history: VecDeque<U256>,
    congestion_detector: CongestionDetector,
    optimal_timing: OptimalTimingPredictor,
}

pub struct CongestionDetector {
    recent_block_times: VecDeque<u64>,
    gas_price_percentiles: [U256; 5], // 10%, 25%, 50%, 75%, 90%
}

pub struct OptimalTimingPredictor {
    historical_patterns: Vec<GasPattern>,
}

#[derive(Debug, Clone)]
pub struct GasPattern {
    hour_of_day: u8,
    day_of_week: u8,
    avg_gas_price: U256,
    volatility: f64,
}

impl GasOptimizer {
    pub fn new() -> Self {
        Self {
            gas_price_history: VecDeque::with_capacity(1000),
            congestion_detector: CongestionDetector::new(),
            optimal_timing: OptimalTimingPredictor::new(),
        }
    }
    
    pub async fn get_optimal_gas_price(&self, urgency: UrgencyLevel) -> Result<U256> {
        let current_gas = self.get_current_gas_price().await?;
        let congestion_level = self.congestion_detector.get_congestion_level();
        
        let multiplier = match urgency {
            UrgencyLevel::Immediate => 1.5,  // 50% above current
            UrgencyLevel::Fast => 1.2,       // 20% above current
            UrgencyLevel::Standard => 1.0,   // Current price
            UrgencyLevel::Slow => 0.8,       // 20% below current
        };
        
        let congestion_adjustment = 1.0 + (congestion_level * 0.5);
        let final_multiplier = multiplier * congestion_adjustment;
        
        Ok(current_gas * U256::from((final_multiplier * 100.0) as u64) / U256::from(100))
    }
    
    pub async fn predict_optimal_execution_time(&self) -> Result<OptimalExecutionWindow> {
        let current_time = chrono::Utc::now();
        let predicted_low_gas_periods = self.optimal_timing.predict_low_gas_periods();
        
        // Find next optimal window within 24 hours
        for window in predicted_low_gas_periods {
            if window.start_time > current_time && 
               window.start_time < current_time + chrono::Duration::hours(24) {
                return Ok(window);
            }
        }
        
        // If no optimal window found, execute immediately
        Ok(OptimalExecutionWindow {
            start_time: current_time,
            end_time: current_time + chrono::Duration::minutes(5),
            expected_gas_savings_pct: 0.0,
            confidence: 0.5,
        })
    }
    
    async fn get_current_gas_price(&self) -> Result<U256> {
        // This would connect to actual gas price oracle
        Ok(U256::from(20_000_000_000u64)) // 20 gwei
    }
}

#[derive(Debug, Clone)]
pub enum UrgencyLevel {
    Immediate,  // Execute now regardless of gas cost
    Fast,       // Execute within 1 block
    Standard,   // Execute within 5 blocks
    Slow,       // Execute when gas is optimal
}

#[derive(Debug, Clone)]
pub struct OptimalExecutionWindow {
    pub start_time: chrono::DateTime<chrono::Utc>,
    pub end_time: chrono::DateTime<chrono::Utc>,
    pub expected_gas_savings_pct: f64,
    pub confidence: f64,
}

impl CongestionDetector {
    pub fn new() -> Self {
        Self {
            recent_block_times: VecDeque::with_capacity(100),
            gas_price_percentiles: [U256::zero(); 5],
        }
    }
    
    pub fn get_congestion_level(&self) -> f64 {
        // Calculate congestion based on block times and gas prices
        let avg_block_time = self.recent_block_times.iter().sum::<u64>() as f64 / 
                            self.recent_block_times.len() as f64;
        
        // Normal Ethereum block time is ~12 seconds
        let time_factor = (avg_block_time / 12.0).min(2.0); // Cap at 2x
        
        // Gas price factor (high gas = high congestion)
        let current_gas = self.gas_price_percentiles[2]; // median
        let gas_factor = if current_gas > U256::from(50_000_000_000u64) { // > 50 gwei
            2.0
        } else if current_gas > U256::from(20_000_000_000u64) { // > 20 gwei
            1.5
        } else {
            1.0
        };
        
        ((time_factor + gas_factor) / 2.0 - 1.0).max(0.0).min(1.0)
    }
}

impl OptimalTimingPredictor {
    pub fn new() -> Self {
        Self {
            historical_patterns: Vec::new(),
        }
    }
    
    pub fn predict_low_gas_periods(&self) -> Vec<OptimalExecutionWindow> {
        let mut windows = Vec::new();
        let now = chrono::Utc::now();
        
        // Typical low gas periods: weekends, early morning UTC
        for day_offset in 0..7 {
            let target_day = now + chrono::Duration::days(day_offset);
            
            // Weekend early morning (2-6 AM UTC)
            if target_day.weekday() == chrono::Weekday::Sat || 
               target_day.weekday() == chrono::Weekday::Sun {
                let start = target_day.date_naive().and_hms_opt(2, 0, 0).unwrap()
                    .and_local_timezone(chrono::Utc).unwrap();
                let end = start + chrono::Duration::hours(4);
                
                windows.push(OptimalExecutionWindow {
                    start_time: start,
                    end_time: end,
                    expected_gas_savings_pct: 25.0,
                    confidence: 0.8,
                });
            }
        }
        
        windows
    }
}
