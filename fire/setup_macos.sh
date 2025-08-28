#!/bin/bash
# setup_macos.sh - macOS-specific setup with Python 3.11 and proper validation

set -e

echo "======================================"
echo "   DeFi Bot macOS Setup               "
echo "======================================"
echo ""

# Check Python version and suggest downgrade if needed
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 13 ]; then
    echo "⚠️  Python 3.13+ detected. This version has compatibility issues."
    echo "   Installing Python 3.11 for compatibility..."
    echo ""
    
    if ! command -v brew &> /dev/null; then
        echo "Installing Homebrew first..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    brew install python@3.11
    PYTHON_CMD="python3.11"
    PIP_CMD="python3.11 -m pip"
else
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
fi

echo "Using Python: $($PYTHON_CMD --version)"
echo ""

# Create virtual environment with correct Python version
echo "Creating virtual environment..."
$PYTHON_CMD -m venv venv_bot
source venv_bot/bin/activate

# Upgrade pip first
pip install --upgrade pip

# Install compatible requirements
cat > requirements_macos.txt << EOF
web3==6.11.3
aiohttp==3.9.1
python-dotenv==1.0.0
requests==2.31.0
websockets==12.0
numpy==1.24.3
pandas==2.0.3
eth-account==0.10.0
eth-abi==4.2.1
hexbytes==0.3.1
colorama==0.4.6
discord-webhook==1.3.0
EOF

echo "Installing Python packages..."
pip install -r requirements_macos.txt

echo ""
echo "======================================"
echo "   Ethereum Wallet Setup              "
echo "======================================"
echo ""

# Function to generate new Ethereum wallet
generate_wallet() {
    python3 << 'EOF'
from eth_account import Account
import secrets

# Generate new account
priv_key = '0x' + secrets.token_hex(32)
account = Account.from_key(priv_key)

print('Generated new Ethereum wallet:')
print('================================')
print(f'Address: {account.address}')
print(f'Private Key: {priv_key}')
print('================================')
print('⚠️  SAVE YOUR PRIVATE KEY SECURELY!')
print('Never share it with anyone!')
EOF
}

echo "Do you have an Ethereum wallet for testnet?"
echo "1) Yes, I have a wallet"
echo "2) No, generate a new one for me"
read -p "Enter choice (1-2): " WALLET_CHOICE

if [ "$WALLET_CHOICE" == "2" ]; then
    generate_wallet
    echo ""
    echo "Copy the above credentials, then press Enter to continue..."
    read
fi

echo ""
echo "======================================"
echo "   API Keys Configuration             "
echo "======================================"
echo ""

# Validate Ethereum address format
validate_eth_address() {
    local address=$1
    if [[ $address =~ ^0x[a-fA-F0-9]{40}$ ]]; then
        echo "valid"
    else
        echo "error:Invalid Ethereum address format. Must start with 0x and be 42 characters"
    fi
}

# Get Ethereum credentials
while true; do
    read -sp "Enter your PRIVATE_KEY (must start with 0x): " PRIVATE_KEY
    echo ""
    
    if [[ ! $PRIVATE_KEY =~ ^0x[a-fA-F0-9]{64}$ ]]; then
        echo "❌ Invalid private key format. Must start with 0x and be 66 characters"
        echo "Example: 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        continue
    fi
    
    read -p "Enter your WALLET_ADDRESS (must start with 0x): " WALLET_ADDRESS
    
    ADDR_VALID=$(validate_eth_address "$WALLET_ADDRESS")
    if [[ "$ADDR_VALID" != "valid" ]]; then
        echo "❌ $ADDR_VALID"
        echo "Example: 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb4"
        continue
    fi
    
    echo "✅ Valid Ethereum credentials"
    break
done

echo ""
echo "--- RPC Provider Setup ---"
echo "Get your Alchemy API key from: https://www.alchemy.com/"
read -p "Enter ALCHEMY_API_KEY: " ALCHEMY_API_KEY

echo ""
echo "--- Etherscan Setup ---"
echo "Get your API key from: https://etherscan.io/apis"
read -p "Enter ETHERSCAN_API_KEY: " ETHERSCAN_API_KEY

echo ""
echo "--- OKX Testnet Setup ---"
echo "Get testnet API from: https://www.okx.com/testnet"
echo "⚠️  Make sure to use TESTNET credentials, not mainnet!"
read -p "Enter OKX_API_KEY: " OKX_API_KEY
read -sp "Enter OKX_SECRET_KEY: " OKX_SECRET_KEY
echo ""
read -p "Enter OKX_PASSPHRASE: " OKX_PASSPHRASE

echo ""
echo "--- Discord Setup ---"
echo "Create webhook: Server Settings → Integrations → Webhooks"
read -p "Enter DISCORD_WEBHOOK_URL: " DISCORD_WEBHOOK_URL

# Test basic connectivity
echo ""
echo "Testing connections..."

# Test Alchemy
echo -n "Testing Alchemy RPC... "
TEST_RESULT=$(curl -s -X POST "https://eth-sepolia.g.alchemy.com/v2/$ALCHEMY_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
    | grep -o '"result"' || echo "failed")

if [ "$TEST_RESULT" == '"result"' ]; then
    echo "✅"
else
    echo "⚠️  Failed (check your API key)"
fi

# Create configuration
cat > .env.testnet << EOF
# Network Configuration
NETWORK=sepolia
CHAIN_ID=11155111

# Wallet Configuration
PRIVATE_KEY=$PRIVATE_KEY
WALLET_ADDRESS=$WALLET_ADDRESS

# API Keys
ALCHEMY_API_KEY=$ALCHEMY_API_KEY
INFURA_API_KEY=
ETHERSCAN_API_KEY=$ETHERSCAN_API_KEY

# OKX Configuration
OKX_API_KEY=$OKX_API_KEY
OKX_SECRET_KEY=$OKX_SECRET_KEY
OKX_PASSPHRASE=$OKX_PASSPHRASE

# Discord
DISCORD_WEBHOOK_URL=$DISCORD_WEBHOOK_URL

# Trading Parameters
MAX_GAS_PRICE_GWEI=100
MIN_PROFIT_USD=10
MAX_POSITION_SIZE_ETH=0.1
SLIPPAGE_TOLERANCE=0.03

# Contract Addresses (will be filled after deployment)
FLASHLOAN_CONTRACT_ADDRESS=
MULTICALL_CONTRACT_ADDRESS=

# RPC URLs
MAINNET_RPC=https://eth-sepolia.g.alchemy.com/v2/
EOF

echo ""
echo "✅ Configuration saved to .env.testnet"
echo ""

# Create simplified Python test file
cat > test_connection.py << 'EOF'
#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from web3 import Web3
import requests

load_dotenv('.env.testnet')

def test_connections():
    print("\n🔍 Testing all connections...\n")
    
    # Test Web3
    try:
        w3 = Web3(Web3.HTTPProvider(f"https://eth-sepolia.g.alchemy.com/v2/{os.getenv('ALCHEMY_API_KEY')}"))
        if w3.is_connected():
            block = w3.eth.block_number
            print(f"✅ Web3 Connected - Block: {block}")
            
            # Check wallet balance
            balance = w3.eth.get_balance(os.getenv('WALLET_ADDRESS'))
            eth_balance = w3.from_wei(balance, 'ether')
            print(f"✅ Wallet Balance: {eth_balance} ETH")
            
            if eth_balance == 0:
                print("⚠️  No testnet ETH - Get some from: https://sepoliafaucet.com/")
        else:
            print("❌ Web3 connection failed")
    except Exception as e:
        print(f"❌ Web3 error: {e}")
    
    # Test Discord
    try:
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        if webhook_url and 'discord.com' in webhook_url:
            print("✅ Discord webhook configured")
        else:
            print("⚠️  Discord webhook not configured")
    except Exception as e:
        print(f"❌ Discord error: {e}")
    
    print("\n" + "="*50)

if __name__ == "__main__":
    test_connections()
EOF

chmod +x test_connection.py

echo "======================================"
echo "   Testing Configuration              "
echo "======================================"

python test_connection.py

echo ""
echo "======================================"
echo "   Next Steps                         "
echo "======================================"
echo ""
echo "1. Get testnet ETH from:"
echo "   - https://sepoliafaucet.com/"
echo "   - https://www.alchemy.com/faucets/ethereum-sepolia"
echo ""
echo "2. Deploy contracts:"
echo "   ./deploy_contracts.sh"
echo ""
echo "3. Run the bot:"
echo "   source venv_bot/bin/activate"
echo "   python main.py"
echo ""
echo "✅ Setup complete!"