from fastapi import FastAPI
import uvicorn
import asyncio
import logging

app = FastAPI()

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "arbitrage-bot",
        "timestamp": time.time()
    }

@app.get("/status")
async def bot_status():
    # This could be enhanced to check actual bot status
    return {
        "arbitrage_engine": "running",
        "market_data": "connected", 
        "exchanges": "monitoring",
        "ai_training": "active"
    }

def start_health_server():
    """Start health check server in background"""
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

if __name__ == "__main__":
    start_health_server()
