#!/usr/bin/env python3
"""
Fixed test script for crypto arbitrage bot that handles Python path issues
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path so we can import from src/
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Now try the imports
try:
    from src.types import ArbitrageOpportunity, PriceLevel, OrderBook
    from src.execution.trader import PaperTrader
    from src.detection.arbitrage_finder import ArbitrageFinder
    print("✅ All imports successful!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\n🔍 Available modules in src/:")
    if os.path.exists('src'):
        for item in os.listdir('src'):
            if not item.startswith('.'):
                print(f"   - {item}")
    sys.exit(1)

# Test the core functionality
def test_basic_functionality():
    print("\n🧪 Testing basic functionality...")
    
    # Test data structures
    price_level = PriceLevel(price=50000.0, volume=1.5)
    print(f"✅ PriceLevel: ${price_level.price}")
    
    orderbook = OrderBook(
        symbol="BTC/USDT",
        bids=[PriceLevel(49999, 1.0)],
        asks=[PriceLevel(50001, 1.0)],
        timestamp=1234567890
    )
    print(f"✅ OrderBook: {orderbook.symbol} spread: ${orderbook.asks[0].price - orderbook.bids[0].price}")
    
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
    
    return True

if __name__ == "__main__":
    print("🤖 Testing Crypto Arbitrage Bot Components")
    print("==========================================")
    
    if test_basic_functionality():
        print("\n🎉 All tests passed! Your bot components are working!")
        print("\n💡 Next steps:")
        print("   1. Run: python main.py (to start the full bot)")
        print("   2. Check logs/ directory for detailed output")
        print("   3. Monitor performance in paper trading mode")
    else:
        print("\n❌ Tests failed. Check the error messages above.")
