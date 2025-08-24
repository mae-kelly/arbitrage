#!/bin/bash
echo "📦 Installing MEV Bot dependencies..."

# Install Python dependencies
pip3 install -r requirements.txt

# Install Node dependencies
npm install

# Install Rust
if ! command -v cargo &> /dev/null; then
    echo "Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source $HOME/.cargo/env
fi

# Build Rust components
cargo build --release

echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Fund your wallet with ETH"
echo "3. Deploy contracts: npm run deploy"
echo "4. Run bot: python3 run_bot.py"
