#!/bin/bash
echo "🚀 Activating crypto-arbitrage development environment..."

# Activate Python virtual environment
source venv/bin/activate
echo "✅ Python virtual environment activated"

# Set up Rust environment
source ~/.cargo/env
echo "✅ Rust environment loaded"

# Set up Julia environment
export PATH="$HOME/.juliaup/bin:$PATH"
echo "✅ Julia environment loaded"

# Set up Go environment
export PATH=$PATH:/usr/local/go/bin
echo "✅ Go environment loaded"

echo "🎉 Development environment ready!"
echo "Current directory: $(pwd)"
echo "Python: $(python --version)"
echo "Rust: $(rustc --version)"
echo "Go: $(go version)"
if command -v julia &> /dev/null; then
    echo "Julia: $(julia --version)"
fi

echo ""
echo "📋 Next steps:"
echo "1. Run: ./activate_env.sh (to activate this environment in future sessions)"
echo "2. Test the setup: python -c 'import redis, web3, ccxt; print(\"All imports working!\")'"
echo "3. Start building your arbitrage system!"
