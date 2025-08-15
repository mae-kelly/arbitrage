//! Production ML Engine for Arbitrage Bot

use candle_core::{Device, Tensor, Result as CandleResult};
use candle_nn::{Linear, Module, VarBuilder, Embedding, LSTM, Conv1d};
use candle_transformers::models::llama::LlamaConfig;
use std::collections::HashMap;
use anyhow::Result;
use tokio::sync::RwLock;
use std::sync::Arc;

pub mod price_prediction;
pub mod opportunity_scoring;
pub mod risk_assessment;
pub mod execution_timing;

pub struct MLEngine {
    device: Device,
    models: Arc<RwLock<ModelRegistry>>,
    inference_cache: Arc<RwLock<HashMap<String, CachedPrediction>>>,
}

#[derive(Debug, Clone)]
pub struct CachedPrediction {
    pub prediction: f64,
    pub confidence: f64,
    pub timestamp: std::time::Instant,
    pub features_hash: u64,
}

pub struct ModelRegistry {
    pub price_predictor: Option<price_prediction::PricePredictionModel>,
    pub opportunity_scorer: Option<opportunity_scoring::OpportunityScorer>,
    pub risk_assessor: Option<risk_assessment::RiskAssessmentModel>,
    pub execution_timer: Option<execution_timing::ExecutionTimingModel>,
}

impl MLEngine {
    pub fn new() -> Result<Self> {
        let device = Device::new_cuda(0).unwrap_or(Device::Cpu);
        
        Ok(Self {
            device,
            models: Arc::new(RwLock::new(ModelRegistry {
                price_predictor: None,
                opportunity_scorer: None,
                risk_assessor: None,
                execution_timer: None,
            })),
            inference_cache: Arc::new(RwLock::new(HashMap::new())),
        })
    }
    
    pub async fn initialize_models(&self) -> Result<()> {
        let mut models = self.models.write().await;
        
        // Load trained models
        models.price_predictor = Some(
            price_prediction::PricePredictionModel::load_trained("models/price_predictor.safetensors", &self.device)?
        );
        
        models.opportunity_scorer = Some(
            opportunity_scoring::OpportunityScorer::load_trained("models/opportunity_scorer.safetensors", &self.device)?
        );
        
        models.risk_assessor = Some(
            risk_assessment::RiskAssessmentModel::load_trained("models/risk_assessor.safetensors", &self.device)?
        );
        
        models.execution_timer = Some(
            execution_timing::ExecutionTimingModel::load_trained("models/execution_timer.safetensors", &self.device)?
        );
        
        Ok(())
    }
    
    pub async fn predict_price_movement(
        &self,
        symbol: &str,
        market_features: &[f64],
        timeframe_minutes: u32,
    ) -> Result<PricePrediction> {
        let cache_key = format!("price_{}_{}", symbol, timeframe_minutes);
        
        // Check cache first
        if let Some(cached) = self.get_cached_prediction(&cache_key).await {
            if cached.timestamp.elapsed().as_secs() < 30 { // 30 second cache
                return Ok(PricePrediction {
                    predicted_change_pct: cached.prediction,
                    confidence: cached.confidence,
                    timeframe_minutes,
                    features_used: market_features.len(),
                });
            }
        }
        
        let models = self.models.read().await;
        if let Some(predictor) = &models.price_predictor {
            let features_tensor = Tensor::from_slice(market_features, (1, market_features.len()), &self.device)?;
            let prediction = predictor.predict(&features_tensor).await?;
            
            // Cache the result
            self.cache_prediction(cache_key, prediction.predicted_change_pct, prediction.confidence).await;
            
            Ok(prediction)
        } else {
            Err(anyhow::anyhow!("Price prediction model not loaded"))
        }
    }
    
    pub async fn score_opportunity(
        &self,
        opportunity_features: &OpportunityFeatures,
    ) -> Result<OpportunityScore> {
        let models = self.models.read().await;
        if let Some(scorer) = &models.opportunity_scorer {
            scorer.score_opportunity(opportunity_features).await
        } else {
            Err(anyhow::anyhow!("Opportunity scorer not loaded"))
        }
    }
    
    pub async fn assess_risk(
        &self,
        trade_features: &TradeFeatures,
    ) -> Result<RiskAssessment> {
        let models = self.models.read().await;
        if let Some(assessor) = &models.risk_assessor {
            assessor.assess_risk(trade_features).await
        } else {
            Err(anyhow::anyhow!("Risk assessor not loaded"))
        }
    }
    
    pub async fn optimize_execution_timing(
        &self,
        market_conditions: &MarketConditions,
    ) -> Result<ExecutionTiming> {
        let models = self.models.read().await;
        if let Some(timer) = &models.execution_timer {
            timer.optimize_timing(market_conditions).await
        } else {
            Err(anyhow::anyhow!("Execution timer not loaded"))
        }
    }
    
    async fn get_cached_prediction(&self, key: &str) -> Option<CachedPrediction> {
        self.inference_cache.read().await.get(key).cloned()
    }
    
    async fn cache_prediction(&self, key: String, prediction: f64, confidence: f64) {
        let mut cache = self.inference_cache.write().await;
        cache.insert(key, CachedPrediction {
            prediction,
            confidence,
            timestamp: std::time::Instant::now(),
            features_hash: 0, // TODO: implement proper hashing
        });
    }
}

#[derive(Debug, Clone)]
pub struct PricePrediction {
    pub predicted_change_pct: f64,
    pub confidence: f64,
    pub timeframe_minutes: u32,
    pub features_used: usize,
}

#[derive(Debug, Clone)]
pub struct OpportunityFeatures {
    pub price_difference_pct: f64,
    pub volume_ratio: f64,
    pub liquidity_score: f64,
    pub spread_bps: f64,
    pub market_volatility: f64,
    pub time_since_last_update: f64,
    pub exchange_reliability_scores: Vec<f64>,
}

#[derive(Debug, Clone)]
pub struct OpportunityScore {
    pub overall_score: f64,  // 0-1
    pub profit_probability: f64,
    pub execution_probability: f64,
    pub risk_adjusted_score: f64,
    pub recommended_position_size: f64,
}

#[derive(Debug, Clone)]
pub struct TradeFeatures {
    pub position_size_usd: f64,
    pub leverage: f64,
    pub holding_period_expected: f64,
    pub correlation_with_portfolio: f64,
    pub volatility_percentile: f64,
    pub liquidity_ratio: f64,
}

#[derive(Debug, Clone)]
pub struct RiskAssessment {
    pub overall_risk_score: f64,  // 0-1
    pub var_95_percent: f64,
    pub expected_max_drawdown: f64,
    pub liquidity_risk: f64,
    pub correlation_risk: f64,
    pub recommended_stop_loss: f64,
}

#[derive(Debug, Clone)]
pub struct MarketConditions {
    pub volatility: f64,
    pub volume: f64,
    pub spread: f64,
    pub order_book_depth: f64,
    pub time_of_day: f64,
    pub gas_price: f64,
    pub network_congestion: f64,
}

#[derive(Debug, Clone)]
pub struct ExecutionTiming {
    pub optimal_delay_ms: u64,
    pub urgency_score: f64,
    pub expected_slippage: f64,
    pub gas_optimization_delay: u64,
    pub market_impact_estimate: f64,
}
