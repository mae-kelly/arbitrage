//! ML-based execution timing optimization

use candle_core::{Device, Tensor, Result as CandleResult};
use candle_nn::{Linear, Module, VarBuilder, LSTM};
use anyhow::Result;
use super::{MarketConditions, ExecutionTiming};

pub struct ExecutionTimingModel {
    lstm: LSTM,
    timing_head: Linear,
    slippage_head: Linear,
    gas_head: Linear,
    device: Device,
}

impl ExecutionTimingModel {
    pub fn new(device: &Device) -> CandleResult<Self> {
        let vb = VarBuilder::zeros(candle_core::DType::F32, device);
        
        let lstm = LSTM::new(7, 128, vb.pp("lstm"))?; // 7 input features
        let timing_head = Linear::new(128, 1, vb.pp("timing"))?;
        let slippage_head = Linear::new(128, 1, vb.pp("slippage"))?;
        let gas_head = Linear::new(128, 1, vb.pp("gas"))?;
        
        Ok(Self {
            lstm,
            timing_head,
            slippage_head,
            gas_head,
            device: device.clone(),
        })
    }
    
    pub fn load_trained(model_path: &str, device: &Device) -> Result<Self> {
        let mut model = Self::new(device)?;
        
        tracing::info!("Loading trained execution timing model from {}", model_path);
        
        Ok(model)
    }
    
    pub async fn optimize_timing(&self, conditions: &MarketConditions) -> Result<ExecutionTiming> {
        let start_time = std::time::Instant::now();
        
        // Convert market conditions to features
        let features = vec![
            conditions.volatility,
            conditions.volume,
            conditions.spread,
            conditions.order_book_depth,
            conditions.time_of_day,
            conditions.gas_price,
            conditions.network_congestion,
        ];
        
        let input_tensor = Tensor::from_slice(
            &features,
            (1, 1, features.len()), // (batch, sequence, features)
            &self.device
        )?;
        
        // LSTM forward pass
        let (lstm_output, _) = self.lstm.forward(&input_tensor)?;
        let last_hidden = lstm_output.get(0)?.get(0)?; // Get last timestep
        
        // Get predictions from heads
        let optimal_delay = self.timing_head.forward(&last_hidden)?;
        let expected_slippage = self.slippage_head.forward(&last_hidden)?;
        let gas_delay = self.gas_head.forward(&last_hidden)?;
        
        // Extract values and apply constraints
        let optimal_delay_ms = (optimal_delay.to_scalar::<f64>()? * 10000.0).max(0.0).min(60000.0) as u64; // 0-60 seconds
        let slippage = expected_slippage.to_scalar::<f64>()?.max(0.0).min(0.1); // 0-10% slippage
        let gas_optimization_delay = (gas_delay.to_scalar::<f64>()? * 30000.0).max(0.0).min(300000.0) as u64; // 0-5 minutes
        
        // Calculate urgency score
        let urgency_score = if conditions.volatility > 0.05 || conditions.spread > 100.0 {
            0.9 // High urgency
        } else if conditions.network_congestion > 0.7 {
            0.3 // Low urgency due to congestion
        } else {
            0.6 // Medium urgency
        };
        
        // Market impact estimation
        let market_impact = (conditions.volume / 1000000.0).min(0.02); // Max 2% impact
        
        let inference_time = start_time.elapsed();
        
        tracing::debug!(
            "Execution timing optimization completed in {}μs: delay={}ms, urgency={:.3}",
            inference_time.as_micros(),
            optimal_delay_ms,
            urgency_score
        );
        
        Ok(ExecutionTiming {
            optimal_delay_ms,
            urgency_score,
            expected_slippage: slippage,
            gas_optimization_delay,
            market_impact_estimate: market_impact,
        })
    }
}
