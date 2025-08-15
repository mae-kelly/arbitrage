#!/usr/bin/env python3
"""Production ML inference server with caching and monitoring"""

import asyncio
import time
import logging
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import redis.asyncio as redis
import json
import torch
import numpy as np
from pydantic import BaseModel
import sys
import os

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from models.trained.model_loader import load_production_models
from src.ml_engine import OpportunityFeatures, TradeFeatures, MarketConditions

app = FastAPI(
    title="Arbitrage ML API",
    version="2.0.0",
    description="Production ML inference for arbitrage trading"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
models = {}
redis_client = None
inference_stats = {
    "total_requests": 0,
    "cache_hits": 0,
    "avg_inference_time": 0.0,
    "model_load_time": 0.0
}

class PredictionRequest(BaseModel):
    features: List[float]
    model_type: str
    use_cache: bool = True
    cache_ttl: int = 30

class OpportunityRequest(BaseModel):
    price_difference_pct: float
    volume_ratio: float
    liquidity_score: float
    spread_bps: float
    market_volatility: float
    time_since_last_update: float
    exchange_reliability_scores: List[float]

class RiskRequest(BaseModel):
    position_size_usd: float
    leverage: float
    holding_period_expected: float
    correlation_with_portfolio: float
    volatility_percentile: float
    liquidity_ratio: float

class TimingRequest(BaseModel):
    volatility: float
    volume: float
    spread: float
    order_book_depth: float
    time_of_day: float
    gas_price: float
    network_congestion: float

@app.on_event("startup")
async def startup_event():
    global models, redis_client
    
    logging.info("🚀 Starting production ML inference server...")
    
    # Load models
    start_time = time.time()
    models = load_production_models()
    inference_stats["model_load_time"] = time.time() - start_time
    
    # Connect to Redis
    redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
    
    logging.info(f"✅ Server ready! Model load time: {inference_stats['model_load_time']:.2f}s")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "models_loaded": len(models),
        "uptime_seconds": time.time(),
        "inference_stats": inference_stats
    }

@app.post("/predict/price")
async def predict_price(request: PredictionRequest):
    """Price movement prediction"""
    start_time = time.time()
    inference_stats["total_requests"] += 1
    
    try:
        # Check cache
        if request.use_cache:
            cache_key = f"price_pred:{hash(tuple(request.features))}"
            cached = await redis_client.get(cache_key)
            if cached:
                inference_stats["cache_hits"] += 1
                return json.loads(cached)
        
        # Run inference
        features_tensor = torch.FloatTensor(request.features).unsqueeze(0)
        
        with torch.no_grad():
            prediction = await models['price_predictor'].predict(features_tensor)
        
        result = {
            "predicted_change_pct": prediction.predicted_change_pct,
            "confidence": prediction.confidence,
            "inference_time_ms": (time.time() - start_time) * 1000,
            "model_version": "v3.2.1"
        }
        
        # Cache result
        if request.use_cache:
            await redis_client.setex(cache_key, request.cache_ttl, json.dumps(result))
        
        # Update stats
        inference_stats["avg_inference_time"] = (
            inference_stats["avg_inference_time"] * 0.99 + 
            result["inference_time_ms"] * 0.01
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict/opportunity")
async def predict_opportunity(request: OpportunityRequest):
    """Opportunity scoring prediction"""
    start_time = time.time()
    inference_stats["total_requests"] += 1
    
    try:
        opportunity = OpportunityFeatures(
            price_difference_pct=request.price_difference_pct,
            volume_ratio=request.volume_ratio,
            liquidity_score=request.liquidity_score,
            spread_bps=request.spread_bps,
            market_volatility=request.market_volatility,
            time_since_last_update=request.time_since_last_update,
            exchange_reliability_scores=request.exchange_reliability_scores
        )
        
        score = await models['opportunity_scorer'].score_opportunity(opportunity)
        
        result = {
            "overall_score": score.overall_score,
            "profit_probability": score.profit_probability,
            "execution_probability": score.execution_probability,
            "risk_adjusted_score": score.risk_adjusted_score,
            "recommended_position_size": score.recommended_position_size,
            "inference_time_ms": (time.time() - start_time) * 1000,
            "model_version": "v2.1.4"
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict/risk")
async def predict_risk(request: RiskRequest):
    """Risk assessment prediction"""
    start_time = time.time()
    inference_stats["total_requests"] += 1
    
    try:
        trade_features = TradeFeatures(
            position_size_usd=request.position_size_usd,
            leverage=request.leverage,
            holding_period_expected=request.holding_period_expected,
            correlation_with_portfolio=request.correlation_with_portfolio,
            volatility_percentile=request.volatility_percentile,
            liquidity_ratio=request.liquidity_ratio
        )
        
        risk = await models['risk_assessor'].assess_risk(trade_features)
        
        result = {
            "overall_risk_score": risk.overall_risk_score,
            "var_95_percent": risk.var_95_percent,
            "expected_max_drawdown": risk.expected_max_drawdown,
            "liquidity_risk": risk.liquidity_risk,
            "correlation_risk": risk.correlation_risk,
            "recommended_stop_loss": risk.recommended_stop_loss,
            "inference_time_ms": (time.time() - start_time) * 1000,
            "model_version": "v1.8.2"
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict/timing")
async def predict_timing(request: TimingRequest):
    """Execution timing optimization"""
    start_time = time.time()
    inference_stats["total_requests"] += 1
    
    try:
        market_conditions = MarketConditions(
            volatility=request.volatility,
            volume=request.volume,
            spread=request.spread,
            order_book_depth=request.order_book_depth,
            time_of_day=request.time_of_day,
            gas_price=request.gas_price,
            network_congestion=request.network_congestion
        )
        
        timing = await models['execution_timer'].optimize_timing(market_conditions)
        
        result = {
            "optimal_delay_ms": timing.optimal_delay_ms,
            "urgency_score": timing.urgency_score,
            "expected_slippage": timing.expected_slippage,
            "gas_optimization_delay": timing.gas_optimization_delay,
            "market_impact_estimate": timing.market_impact_estimate,
            "inference_time_ms": (time.time() - start_time) * 1000,
            "model_version": "v1.4.7"
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models/performance")
async def get_model_performance():
    """Get model performance metrics"""
    with open("models/artifacts/performance_benchmarks.json", 'r') as f:
        benchmarks = json.load(f)
    
    return {
        "benchmarks": benchmarks,
        "runtime_stats": inference_stats,
        "cache_hit_rate": inference_stats["cache_hits"] / max(inference_stats["total_requests"], 1)
    }

@app.get("/models/versions")
async def get_model_versions():
    """Get loaded model versions"""
    return {
        "price_predictor": "v3.2.1",
        "opportunity_scorer": "v2.1.4", 
        "risk_assessor": "v1.8.2",
        "execution_timer": "v1.4.7",
        "server_version": "v2.0.0"
    }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        workers=4,
        loop="uvloop",
        access_log=False
    )
