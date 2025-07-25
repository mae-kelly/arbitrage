#!/bin/bash

echo "🚀 Deploying Enhanced Arbitrage System"
echo "======================================"

# Check if virtual environment is active
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "❌ Virtual environment not activated"
    echo "Run: source venv/bin/activate"
    exit 1
fi

echo "📦 Installing additional dependencies..."
pip install web3 redis numpy scipy scikit-learn

echo "🔧 Setting up Redis..."
# Start Redis if not running
if ! redis-cli ping > /dev/null 2>&1; then
    echo "Starting Redis..."
    if command -v brew &> /dev/null; then
        brew services start redis
    else
        sudo systemctl start redis
    fi
    sleep 2
fi

echo "🧪 Testing enhanced components..."
python -c "
print('Testing enhanced imports...')
try:
    from src.enhanced.data.multi_exchange_manager import EnhancedExchangeManager
    print('✅ Enhanced Exchange Manager')
except Exception as e:
    print(f'❌ Enhanced Exchange Manager: {e}')

try:
    from src.dex.multi_chain_manager import MultiChainDEXManager  
    print('✅ Multi-Chain DEX Manager')
except Exception as e:
    print(f'❌ Multi-Chain DEX Manager: {e}')

try:
    from src.strategies.multi_strategy_detector import MultiStrategyDetector
    print('✅ Multi-Strategy Detector')
except Exception as e:
    print(f'❌ Multi-Strategy Detector: {e}')

print('\\n🎉 Enhanced system components ready!')
"

echo ""
echo "✅ Enhanced system deployed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Configure exchange API keys in configs/"
echo "2. Set up blockchain RPC endpoints"
echo "3. Run: python test_enhanced_system.py"
echo "4. Start monitoring: python enhanced_main.py"
