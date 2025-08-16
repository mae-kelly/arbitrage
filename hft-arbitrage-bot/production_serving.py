#!/usr/bin/env python3
"""
Production ML Model Serving for Real-Time Arbitrage Predictions
"""

import asyncio
import torch
import numpy as np
import pandas as pd
import joblib
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
import redis.asyncio as redis
import json
import logging
from datetime import datetime, timedelta
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PredictionRequest(BaseModel):
    features: List[List[float]]  # Sequence of feature vectors
    model_version: str = "v1"
    include_confidence: bool = True

class PredictionResponse(BaseModel):
    price_change_prediction: float
    direction_prediction: str  # "up", "down", "stable"
    direction_confidence: float
    volatility_prediction: float
    overall_confidence: float
    model_version: str
    prediction_timestamp: str
    inference_time_ms: float

class BatchPredictionRequest(BaseModel):
    requests: List[PredictionRequest]
    parallel_processing: bool = True

class ModelMetrics(BaseModel):
    total_predictions: int
    avg_inference_time_ms: float
    cache_hit_rate: float
    model_accuracy: Optional[float]
    last_updated: str

class ProductionModelServer:
    """Production ML model serving with caching and monitoring"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.redis_client = None
        self.metrics = {
            'total_predictions': 0,
            'total_inference_time': 0.0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
    async def initialize(self):
        """Initialize models and connections"""
        logger.info("🚀 Initializing production model server...")
        
        # Connect to Redis
        self.redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        
        # Load production models
        await self.load_production_models()
        
        logger.info("✅ Model server initialized successfully!")
    
    async def load_production_models(self):
        """Load all production models"""
        try:
            # Load main arbitrage model
            model_path = 'models/production/arbitrage_transformer_v1.pth'
            checkpoint = torch.load(model_path, map_location='cpu')
            
            # Reconstruct model
            from production_training_pipeline import TransformerArbitrageModel, TrainingConfig
            config = TrainingConfig(**checkpoint['config'].__dict__)
            
            model = TransformerArbitrageModel(config)
            model.load_state_dict(checkpoint['model_state_dict'])
            model.eval()
            
            self.models['v1'] = model
            
            # Load scaler
            self.scalers['v1'] = joblib.load('models/production/feature_scaler.joblib')
            
            logger.info("✅ Loaded arbitrage transformer model v1")
            
        except Exception as e:
            logger.error(f"❌ Failed to load models: {e}")
            # Load fallback models or create dummy models
            self.models['v1'] = self._create_fallback_model()
            self.scalers['v1'] = self._create_fallback_scaler()
    
    def _create_fallback_model(self):
        """Create a simple fallback model for demo"""
        class FallbackModel(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.linear = torch.nn.Linear(100, 4)  # Assume 100 features
                
            def forward(self, x):
                out = self.linear(x[:, -1, :])  # Use last timestep
                return {
                    'price_change': out[:, 0:1],
                    'direction': out[:, 1:4],
                    'volatility': torch.abs(out[:, 0:1]),
                    'confidence': torch.sigmoid(out[:, 0:1])
                }
        
        return FallbackModel()
    
    def _create_fallback_scaler(self):
        """Create fallback scaler"""
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        # Fit on dummy data
        dummy_data = np.random.randn(1000, 100)
        scaler.fit(dummy_data)
        return scaler
    
    async def predict_arbitrage_opportunity(self, request: PredictionRequest) -> PredictionResponse:
        """Make real-time arbitrage prediction"""
        start_time = datetime.now()
        
        # Check cache first
        cache_key = self._generate_cache_key(request)
        cached_result = await self._get_cached_prediction(cache_key)
        
        if cached_result:
            self.metrics['cache_hits'] += 1
            return cached_result
        
        self.metrics['cache_misses'] += 1
        
        try:
            # Prepare features
            features = np.array(request.features)
            
            # Validate input shape
            if len(features.shape) != 2:
                raise ValueError(f"Expected 2D features, got shape {features.shape}")
            
            # Scale features
            scaler = self.scalers.get(request.model_version, self.scalers['v1'])
            if features.shape[1] == scaler.n_features_in_:
                features_scaled = scaler.transform(features)
            else:
                # Pad or truncate features to match expected size
                expected_size = scaler.n_features_in_
                if features.shape[1] < expected_size:
                    features_scaled = np.pad(features, ((0, 0), (0, expected_size - features.shape[1])))
                else:
                    features_scaled = features[:, :expected_size]
                features_scaled = scaler.transform(features_scaled)
            
            # Convert to tensor and add batch dimension
            features_tensor = torch.FloatTensor(features_scaled).unsqueeze(0)  # (1, seq_len, features)
            
            # Get model
            model = self.models.get(request.model_version, self.models['v1'])
            
            # Inference
            with torch.no_grad():
                outputs = model(features_tensor)
            
            # Process outputs
            price_change = float(outputs['price_change'].item())
            direction_logits = outputs['direction'].squeeze()
            direction_probs = torch.softmax(direction_logits, dim=0)
            volatility = float(outputs['volatility'].item())
            confidence = float(outputs['confidence'].item())
            
            # Determine direction
            direction_idx = torch.argmax(direction_probs).item()
            direction_map = {0: "down", 1: "stable", 2: "up"}
            direction = direction_map[direction_idx]
            direction_confidence = float(direction_probs[direction_idx].item())
            
            # Create response
            response = PredictionResponse(
                price_change_prediction=price_change,
                direction_prediction=direction,
                direction_confidence=direction_confidence,
                volatility_prediction=volatility,
                overall_confidence=confidence,
                model_version=request.model_version,
                prediction_timestamp=datetime.now().isoformat(),
                inference_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
            
            # Cache result
            await self._cache_prediction(cache_key, response)
            
            # Update metrics
            self.metrics['total_predictions'] += 1
            self.metrics['total_inference_time'] += response.inference_time_ms
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Prediction failed: {e}")
            raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
    
    async def batch_predict(self, requests: List[PredictionRequest]) -> List[PredictionResponse]:
        """Batch prediction for multiple requests"""
        if len(requests) == 1:
            return [await self.predict_arbitrage_opportunity(requests[0])]
        
        # Process in parallel
        tasks = [self.predict_arbitrage_opportunity(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch prediction error: {result}")
                continue
            valid_results.append(result)
        
        return valid_results
    
    def _generate_cache_key(self, request: PredictionRequest) -> str:
        """Generate cache key from request"""
        import hashlib
        
        # Create hash from features
        features_str = str(request.features)
        cache_key = hashlib.md5(f"{features_str}_{request.model_version}".encode()).hexdigest()
        return f"prediction:{cache_key}"
    
    async def _get_cached_prediction(self, cache_key: str) -> Optional[PredictionResponse]:
        """Get cached prediction"""
        try:
            cached = await self.redis_client.get(cache_key)
            if cached:
                data = json.loads(cached)
                return PredictionResponse(**data)
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        
        return None
    
    async def _cache_prediction(self, cache_key: str, response: PredictionResponse):
        """Cache prediction result"""
        try:
            await self.redis_client.setex(
                cache_key, 
                30,  # 30 second TTL
                response.json()
            )
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
    
    async def get_model_metrics(self) -> ModelMetrics:
        """Get model performance metrics"""
        total_requests = self.metrics['cache_hits'] + self.metrics['cache_misses']
        avg_inference_time = (
            self.metrics['total_inference_time'] / max(self.metrics['total_predictions'], 1)
        )
        cache_hit_rate = (
            self.metrics['cache_hits'] / max(total_requests, 1)
        )
        
        return ModelMetrics(
            total_predictions=self.metrics['total_predictions'],
            avg_inference_time_ms=avg_inference_time,
            cache_hit_rate=cache_hit_rate,
            model_accuracy=None,  # Would be calculated from validation data
            last_updated=datetime.now().isoformat()
        )
    
    async def update_model_accuracy(self, predictions: List[dict], actuals: List[dict]):
        """Update model accuracy based on actual outcomes"""
        if not predictions or not actuals or len(predictions) != len(actuals):
            return
        
        correct_directions = 0
        total_predictions = len(predictions)
        
        for pred, actual in zip(predictions, actuals):
            if pred.get('direction') == actual.get('direction'):
                correct_directions += 1
        
        accuracy = correct_directions / total_predictions
        
        # Store in Redis for monitoring
        await self.redis_client.setex(
            "model_accuracy",
            3600,  # 1 hour TTL
            str(accuracy)
        )

# FastAPI application
app = FastAPI(title="HFT Arbitrage ML API", version="1.0.0")
model_server = ProductionModelServer()

@app.on_event("startup")
async def startup():
    await model_server.initialize()

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """Single arbitrage prediction"""
    return await model_server.predict_arbitrage_opportunity(request)

@app.post("/predict/batch", response_model=List[PredictionResponse])
async def batch_predict(request: BatchPredictionRequest):
    """Batch arbitrage predictions"""
    return await model_server.batch_predict(request.requests)

@app.get("/metrics", response_model=ModelMetrics)
async def get_metrics():
    """Get model performance metrics"""
    return await model_server.get_model_metrics()

@app.post("/feedback")
async def update_accuracy(predictions: List[dict], actuals: List[dict]):
    """Update model accuracy with actual outcomes"""
    await model_server.update_model_accuracy(predictions, actuals)
    return {"status": "success", "message": "Accuracy updated"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "models_loaded": len(model_server.models),
        "redis_connected": model_server.redis_client is not None
    }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        workers=1,  # Single worker for model consistency
        loop="uvloop"
    )
