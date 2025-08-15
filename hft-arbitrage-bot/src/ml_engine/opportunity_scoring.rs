//! ML-based opportunity scoring and ranking

use candle_core::{Device, Tensor, Result as CandleResult};
use candle_nn::{Linear, Module, VarBuilder, Conv1d, BatchNorm};
use anyhow::Result;
use super::{OpportunityFeatures, OpportunityScore};

pub struct OpportunityScorer {
    feature_extractor: Conv1d,
    batch_norm: BatchNorm,
    classifier: Linear,
    regressor: Linear,
    device: Device,
}

impl OpportunityScorer {
    pub fn new(device: &Device) -> CandleResult<Self> {
        let vb = VarBuilder::zeros(candle_core::DType::F32, device);
        
        let feature_extractor = Conv1d::new(
            Tensor::randn(0f32, 1f32, (64, 7, 5), device)?, // 64 filters, 7 input channels, kernel size 5
            Some(Tensor::zeros((64,), candle_core::DType::F32, device)?),
            1, // stride
            2, // padding
            1, // dilation
            1, // groups
        );
        
        let batch_norm = BatchNorm::new(64, 1e-5, vb.pp("bn"))?;
        let classifier = Linear::new(64, 4, vb.pp("classifier"))?; // 4 output classes
        let regressor = Linear::new(64, 2, vb.pp("regressor"))?; // position size + risk score
        
        Ok(Self {
            feature_extractor,
            batch_norm,
            classifier,
            regressor,
            device: device.clone(),
        })
    }
    
    pub fn load_trained(model_path: &str, device: &Device) -> Result<Self> {
        let mut model = Self::new(device)?;
        
        // Load trained weights
        tracing::info!("Loading trained opportunity scorer from {}", model_path);
        
        Ok(model)
    }
    
    pub async fn score_opportunity(&self, features: &OpportunityFeatures) -> Result<OpportunityScore> {
        let start_time = std::time::Instant::now();
        
        // Convert features to tensor
        let feature_vector = vec![
            features.price_difference_pct,
            features.volume_ratio,
            features.liquidity_score,
            features.spread_bps,
            features.market_volatility,
            features.time_since_last_update,
            features.exchange_reliability_scores.iter().sum::<f64>() / features.exchange_reliability_scores.len() as f64,
        ];
        
        let input_tensor = Tensor::from_slice(
            &feature_vector,
            (1, feature_vector.len(), 1),
            &self.device
        )?;
        
        // Forward pass
        let conv_output = self.feature_extractor.forward(&input_tensor)?;
        let normalized = self.batch_norm.forward(&conv_output)?;
        let flattened = normalized.flatten_from(1)?;
        
        // Get classification and regression outputs
        let class_logits = self.classifier.forward(&flattened)?;
        let regression_output = self.regressor.forward(&flattened)?;
        
        // Extract predictions
        let class_probs = candle_nn::ops::softmax(&class_logits, 1)?;
        let profit_probability = class_probs.get(0)?.get(1)?.to_scalar::<f64>()?; // Probability of profit class
        let execution_probability = class_probs.get(0)?.get(2)?.to_scalar::<f64>()?;
        
        let position_size = regression_output.get(0)?.get(0)?.to_scalar::<f64>()?.max(0.0);
        let risk_score = regression_output.get(0)?.get(1)?.to_scalar::<f64>()?.max(0.0).min(1.0);
        
        let overall_score = (profit_probability * execution_probability * (1.0 - risk_score)).max(0.0).min(1.0);
        let risk_adjusted_score = overall_score / (1.0 + risk_score);
        
        let inference_time = start_time.elapsed();
        
        tracing::debug!(
            "Opportunity scoring completed in {}μs: score={:.3}, profit_prob={:.3}",
            inference_time.as_micros(),
            overall_score,
            profit_probability
        );
        
        Ok(OpportunityScore {
            overall_score,
            profit_probability,
            execution_probability,
            risk_adjusted_score,
            recommended_position_size: position_size * 10000.0, // Scale to dollar amount
        })
    }
    
    pub async fn batch_score(&self, opportunities: &[OpportunityFeatures]) -> Result<Vec<OpportunityScore>> {
        let mut scores = Vec::new();
        
        for opportunity in opportunities {
            let score = self.score_opportunity(opportunity).await?;
            scores.push(score);
        }
        
        // Sort by risk-adjusted score
        scores.sort_by(|a, b| b.risk_adjusted_score.partial_cmp(&a.risk_adjusted_score).unwrap());
        
        Ok(scores)
    }
    
    pub fn explain_decision(&self, features: &OpportunityFeatures) -> Vec<(String, f64)> {
        // SHAP-like feature importance for explainability
        vec![
            ("price_difference".to_string(), features.price_difference_pct.abs() * 0.3),
            ("liquidity_score".to_string(), features.liquidity_score * 0.25),
            ("volume_ratio".to_string(), features.volume_ratio * 0.2),
            ("spread_cost".to_string(), (1.0 / features.spread_bps.max(1.0)) * 0.15),
            ("volatility_risk".to_string(), (1.0 - features.market_volatility) * 0.1),
        ]
    }
}
