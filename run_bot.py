#!/usr/bin/env python3
"""
Simple script to test the arbitrage system
"""
import asyncio
from src.data.exchange_manager import ExchangeManager

async def test_system():
    print("🚀 Testing Crypto Arbitrage System...")
    
    # Test exchange manager
    em = ExchangeManager()
    await em.initialize()
    
    print("✅ Exchange Manager initialized")
    
    # Test fetching data
    orderbook = await em.fetch_orderbook('binance', 'BTC/USDT')
    if orderbook:
        print(f"✅ Fetched BTC/USDT orderbook from Binance")
        print(f"   Best bid: ${orderbook['bids'][0][0]}")
        print(f"   Best ask: ${orderbook['asks'][0][0]}")
    
    await em.close()
    print("✅ Test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_system())
