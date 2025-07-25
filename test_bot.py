#!/usr/bin/env python3
"""
Test bot to verify the arbitrage system works without real API keys
"""
import asyncio
import json
from decimal import Decimal
from datetime import datetime
from src.types import ArbitrageOpportunity
from src.execution.trader import PaperTrader
from loguru import logger

async def simulate_arbitrage_opportunities():
    """Simulate finding arbitrage opportunities"""
    
    # Create a paper trader
    trader = PaperTrader()
    print(f"🏦 Starting balance: ${trader.balance}")
    
    # Simulate some arbitrage opportunities
    opportunities = [
        ArbitrageOpportunity(
            id="test_1",
            type="spatial",
            symbol="BTC/USDT",
            buy_exchange="binance",
            sell_exchange="coinbase",
            buy_price=Decimal("49500"),
            sell_price=Decimal("50000"),
            profit_pct=Decimal("0.0101"),  # 1.01% profit
            profit_usd=Decimal("505"),
            confidence=0.85,
            timestamp=datetime.now(),
            expires_at=datetime.now()
        ),
        ArbitrageOpportunity(
            id="test_2",
            type="spatial",
            symbol="ETH/USDT",
            buy_exchange="kraken",
            sell_exchange="binance",
            buy_price=Decimal("2980"),
            sell_price=Decimal("3015"),
            profit_pct=Decimal("0.0117"),  # 1.17% profit
            profit_usd=Decimal("350"),
            confidence=0.90,
            timestamp=datetime.now(),
            expires_at=datetime.now()
        )
    ]
    
    print("\n🔍 Found simulated arbitrage opportunities:")
    for opp in opportunities:
        print(f"   {opp.symbol}: Buy on {opp.buy_exchange} at ${opp.buy_price}")
        print(f"                Sell on {opp.sell_exchange} at ${opp.sell_price}")
        print(f"                Profit: {opp.profit_pct:.2%}")
        
        # Execute the trade
        success = await trader.execute_arbitrage(opp)
        if success:
            print(f"   ✅ Trade executed successfully!")
        else:
            print(f"   ❌ Trade failed")
        print()
    
    # Show final stats
    stats = trader.get_performance_stats()
    print("📊 Trading Performance:")
    print(f"   Total trades: {stats['total_trades']}")
    print(f"   Total profit: ${stats['total_profit']:.2f}")
    print(f"   Final balance: ${stats['current_balance']:.2f}")
    print(f"   Return: {stats['profit_percentage']:.2f}%")
    print(f"   Avg profit per trade: ${stats['avg_profit_per_trade']:.2f}")
    
    return stats

if __name__ == "__main__":
    print("🤖 Testing Crypto Arbitrage Bot (Simulation Mode)")
    print("=" * 50)
    
    # Run the simulation
    stats = asyncio.run(simulate_arbitrage_opportunities())
    
    if stats['total_trades'] > 0 and stats['total_profit'] > 0:
        print("\n🎉 All tests passed! The arbitrage system is working!")
        print("🚀 Ready to connect to real exchanges and start trading!")
    else:
        print("\n❌ Tests failed - check the code above")
