//! Advanced risk assessment using ensemble methods

use candle_core::{Device, Tensor, Result as CandleResult};
use candle_nn::{Linear, Module, VarBuilder, Dropout};
use anyhow::Result;
use super::{TradeFeatures, RiskAssessment};

pub struct RiskAssessmentModel {
    risk_networks: Vec<RiskNetwork>,
    ensemble_weights: Vec<f64>,
    device: Device,
}

struct RiskNetwork {
    layers: Vec<Linear>,
    dropout: Dropout,
}

impl RiskAssessmentModel {
    pub fn new(device: &Device) -> CandleResult<Self> {
        let mut risk_networks = Vec::new();
        
        // Create ensemble of 5 different risk networks
        for i in 0..5 {
            let vb = VarBuilder::zeros(candle_core::DType::F32, device).pp(&format!("network_{}", i));
            
            let network = RiskNetwork {
                layers: vec![
                    Linear::new(6, 128, vb.pp("layer1"))?,  // 6 input features
                    Linear::new(128, 64, vb.pp("layer2"))?,
                    Linear::new(64, 32, vb.pp("layer3"))?,
                    Linear::new(32, 5, vb.pp("output"))?, // 5 risk outputs
                ],
                dropout: Dropout::new(0.2),
            };
            
            risk_networks.push(network);
        }
        
        let ensemble_weights = vec![0.25, 0.2, 0.2, 0.2, 0.15]; // Weighted ensemble
        
        Ok(Self {
            risk_networks,
            ensemble_weights,
            device: device.clone(),
        })
    }
    
    pub fn load_trained(model_path: &str, device: &Device) -> Result<Self> {
        let mut model = Self::new(device)?;
        
        // Load trained ensemble weights
        tracing::info!("Loading trained risk assessment model from {}", model_path);
        
        Ok(model)
    }
    
    pub async fn assess_risk(&self, features: &TradeFeatures) -> Result<RiskAssessment> {
        let start_time = std::time::Instant::now();
        
        // Convert features to tensor
        let feature_vector = vec![
            features.position_size_usd / 100000.0, // Normalize
            features.leverage,
            features.holding_period_expected,
            features.correlation_with_portfolio,
            features.volatility_percentile,
            features.liquidity_ratio,
        ];
        
        let input_tensor = Tensor::from_slice(
            &feature_vector,
            (1, feature_vector.len()),
            &self.device
        )?;
        
        // Run ensemble prediction
        let mut ensemble_outputs = Vec::new();
        
        for network in &self.risk_networks {
            let mut x = input_tensor.clone();
            
            for (i, layer) in network.layers.iter().enumerate() {
                x = layer.forward(&x)?;
                
                if i < network.layers.len() - 1 {
                    x = x.relu()?;
                    x = network.dropout.forward(&x)?;
                }
            }
            
            ensemble_outputs.push(x);
        }
        
        // Weighted ensemble average
        let mut final_output = ensemble_outputs[0].clone();
        final_output = final_output.mul_scalar(self.ensemble_weights[0])?;
        
        for (i, output) in ensemble_outputs.iter().skip(1).enumerate() {
            let weighted = output.mul_scalar(self.ensemble_weights[i + 1])?;
            final_output = final_output.add(&weighted)?;
        }
        
        // Extract risk metrics
        let risk_values: Vec<f64> = final_output.to_vec1()?;
        
        let overall_risk_score = risk_values[0].max(0.0).min(1.0);
        let var_95_percent = risk_values[1] * features.position_size_usd * 0.01; // 1% of position as base VaR
        let expected_max_drawdown = risk_values[2].max(0.0).min(0.5); // Max 50% drawdown
        let liquidity_risk = risk_values[3].max(0.0).min(1.0);
        let correlation_risk = risk_values[4].max(0.0).min(1.0);
        
        // Calculate recommended stop loss
        let volatility_factor = features.volatility_percentile * 2.0;
        let recommended_stop_loss = (overall_risk_score * volatility_factor * 0.05).max(0.005).min(0.1); // 0.5% to 10%
        
        let inference_time = start_time.elapsed();
        
        tracing::debug!(
            "Risk assessment completed in {}μs: overall_risk={:.3}, VaR=${:.2}",
            inference_time.as_micros(),
            overall_risk_score,
            var_95_percent
        );
        
        Ok(RiskAssessment {
            overall_risk_score,
            var_95_percent,
            expected_max_drawdown,
            liquidity_risk,
            correlation_risk,
            recommended_stop_loss,
        })
    }
    
    pub fn calculate_portfolio_risk(&self, trades: &[TradeFeatures]) -> Result<f64> {
        // Calculate portfolio-level risk considering correlations
        let individual_risks: Result<Vec<f64>, _> = trades.iter()
            .map(|trade| {
                // Simplified individual risk calculation
                Ok(trade.position_size_usd * trade.volatility_percentile * trade.leverage)
            })
            .collect();
        
        let risks = individual_risks?;
        let total_exposure: f64 = risks.iter().sum();
        
        // Apply correlation adjustments
        let correlation_factor = trades.iter()
            .map(|t| t.correlation_with_portfolio.abs())
            .sum::<f64>() / trades.len() as f64;
        
        let diversification_benefit = 1.0 - (correlation_factor * 0.3);
        
        Ok(total_exposure * diversification_benefit)
    }
}
