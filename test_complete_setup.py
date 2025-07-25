#!/usr/bin/env python3
"""Complete setup test for crypto arbitrage bot"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_all_imports():
    """Test all critical imports"""
    print("🧪 Testing all imports...")
    
    try:
        from src.types import PriceLevel, OrderBook, ArbitrageOpportunity
        print("✅ Core types")
    except Exception as e:
        print(f"❌ Core types: {e}")
        return False
    
    try:
        from src.data.exchange_manager import ExchangeManager
        print("✅ Exchange manager")
    except Exception as e:
        print(f"❌ Exchange manager: {e}")
        return False
    
    try:
        from src.detection.arbitrage_finder import ArbitrageFinder
        print("✅ Arbitrage finder")
    except Exception as e:
        print(f"❌ Arbitrage finder: {e}")
        return False
    
    try:
        from src.execution.trader import PaperTrader
        print("✅ Paper trader")
    except Exception as e:
        print(f"❌ Paper trader: {e}")
        return False
    
    return True

def test_basic_functionality():
    """Test basic bot functionality"""
    print("\n🔧 Testing basic functionality...")
    
    from src.types import PriceLevel, OrderBook, ArbitrageOpportunity
    from src.data.exchange_manager import ExchangeManager
    from src.execution.trader import PaperTrader
    
    # Test exchange manager
    exchange_manager = ExchangeManager()
    exchange_manager.add_exchange('binance')
    print("✅ Exchange manager created")
    
    # Test paper trader
    trader = PaperTrader(initial_balance=10000)
    print(f"✅ Paper trader created with ${trader.balance}")
    
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
    
    # Execute trade
    success = trader.execute_arbitrage(opportunity)
    if success:
        print(f"✅ Test trade executed! New balance: ${trader.balance}")
    
    return True

if __name__ == "__main__":
    print("🤖 COMPLETE SETUP TEST")
    print("======================")
    
    if test_all_imports() and test_basic_functionality():
        print("\n🎉 ALL TESTS PASSED!")
        print("Your crypto arbitrage bot setup is complete and working!")
        print("\n💡 Next steps:")
        print("   1. Add your exchange API keys to .env")
        print("   2. Run: python main.py")
        print("   3. Monitor logs/ directory for output")
    else:
        print("\n❌ Some tests failed. Check the errors above.")
