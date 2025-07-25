#!/bin/bash
echo "🚀 Activating crypto-arbitrage development environment..."

if [ ! -f "venv/bin/activate" ]; then
    echo "❌ Error: Not in crypto-arbitrage directory or venv not found"
    exit 1
fi

source venv/bin/activate
export PYTHONPATH="$PWD:$PYTHONPATH"

# Load other environments
source ~/.cargo/env 2>/dev/null || true
export PATH="$HOME/.juliaup/bin:$PATH"

echo ""
echo "🎉 Development environment ready!"
echo "Python: $(python --version)"
echo "Balance: $10,000 (paper trading)"
echo ""
echo "📋 Available commands:"
echo "python run_bot.py          # Test basic functionality"
echo "python main.py             # Run full arbitrage bot"
echo "python test_setup.py       # Test all imports"
echo ""
echo "🦀 Rust: cd rust-core && cargo check"
echo "🐹 Go:   cd go-execution && go run main.go"
echo "💎 Julia: julia --project=julia-quant -e 'using CryptoArbitrageQuant; hello_julia()'"
