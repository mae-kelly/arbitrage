#!/usr/bin/env python3
"""Minimal test to verify the setup works"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    print("🧪 Testing imports...")
    
    try:
        from src.types import PriceLevel, OrderBook, ArbitrageOpportunity
        print("✅ Core types imported successfully")
    except Exception as e:
        print(f"❌ Types import failed: {e}")
        return False
    
    try:
        from src.execution.trader import PaperTrader
        print("✅ PaperTrader imported successfully")
    except Exception as e:
        print(f"❌ PaperTrader import failed: {e}")
        return False
    
    return True

def test_functionality():
    print("\n🧪 Testing basic functionality...")
    
    from src.types import PriceLevel, OrderBook, ArbitrageOpportunity
    from src.execution.trader import PaperTrader
    
    # Test data structures
    price_level = PriceLevel(price=50000.0, volume=1.5)
    print(f"✅ PriceLevel: ${price_level.price}")
    
    orderbook = OrderBook(
        symbol="BTC/USDT",
        bids=[PriceLevel(49999, 1.0)],
        asks=[PriceLevel(50001, 1.0)],
        timestamp=1234567890
    )
    print(f"✅ OrderBook: {orderbook.symbol}")
    
    # Test paper trader
    trader = PaperTrader(initial_balance=10000.0)
    print(f"✅ PaperTrader: Starting balance ${trader.balance}")
    
    # Test arbitrage opportunity
    opportunity = ArbitrageOpportunity(
        symbol="BTC/USDT",
        buy_exchange="binance",
        sell_exchange="coinbase",
        buy_price=49500.0,
        sell_price=50000.0,
        profit_percentage=1.01,
        volume=1.0,
        timestamp=1234567890
    )
    print(f"✅ ArbitrageOpportunity: {opportunity.profit_percentage}% profit")
    
    # Execute a test trade
    success = trader.execute_arbitrage(opportunity)
    if success:
        print(f"✅ Trade executed! New balance: ${trader.balance}")
    
    return True

if __name__ == "__main__":
    print("🤖 Minimal Crypto Arbitrage Test")
    print("================================")
    
    if test_imports() and test_functionality():
        print("\n🎉 All tests passed! Your setup is working!")
        print("\n💡 Next steps:")
        print("   1. Run: python main.py (to start the full bot)")
        print("   2. Add exchange API keys when ready")
        print("   3. Start with paper trading mode")
    else:
        print("\n❌ Tests failed. Check the error messages above.")
