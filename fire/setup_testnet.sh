#!/bin/bash
# setup_testnet.sh

set -e

echo "======================================"
echo "   DeFi Trading Bot Testnet Setup    "
echo "======================================"
echo ""

TESTNET_CHOICE=""
while [[ ! "$TESTNET_CHOICE" =~ ^[1-4]$ ]]; do
    echo "Select testnet network:"
    echo "1) Sepolia (Ethereum Testnet)"
    echo "2) Arbitrum Sepolia"
    echo "3) Optimism Sepolia"
    echo "4) Base Sepolia"
    read -p "Enter choice (1-4): " TESTNET_CHOICE
done

case $TESTNET_CHOICE in
    1)
        NETWORK="sepolia"
        CHAIN_ID=11155111
        RPC_BASE="https://eth-sepolia.g.alchemy.com/v2/"
        EXPLORER="https://sepolia.etherscan.io"
        NATIVE_TOKEN="ETH"
        ;;
    2)
        NETWORK="arbitrum-sepolia"
        CHAIN_ID=421614
        RPC_BASE="https://arb-sepolia.g.alchemy.com/v2/"
        EXPLORER="https://sepolia.arbiscan.io"
        NATIVE_TOKEN="ETH"
        ;;
    3)
        NETWORK="optimism-sepolia"
        CHAIN_ID=11155420
        RPC_BASE="https://opt-sepolia.g.alchemy.com/v2/"
        EXPLORER="https://sepolia-optimism.etherscan.io"
        NATIVE_TOKEN="ETH"
        ;;
    4)
        NETWORK="base-sepolia"
        CHAIN_ID=84532
        RPC_BASE="https://base-sepolia.g.alchemy.com/v2/"
        EXPLORER="https://sepolia.basescan.org"
        NATIVE_TOKEN="ETH"
        ;;
esac

echo ""
echo "Selected Network: $NETWORK"
echo "Chain ID: $CHAIN_ID"
echo ""

echo "======================================"
echo "        API Keys Configuration        "
echo "======================================"
echo ""

validate_ethereum_key() {
    local private_key=$1
    local wallet_address=$2
    
    python3 -c "
from eth_account import Account
import sys

try:
    account = Account.from_key('$private_key')
    expected = account.address.lower()
    provided = '$wallet_address'.lower()
    
    if expected == provided:
        print('valid')
    else:
        print(f'error:Address mismatch. Key gives {expected}, you provided {provided}')
except Exception as e:
    print(f'error:{str(e)}')
" 2>/dev/null
}

validate_alchemy() {
    local api_key=$1
    local rpc_url="${RPC_BASE}${api_key}"
    
    python3 -c "
import requests
import sys

try:
    response = requests.post('$rpc_url', 
        json={'jsonrpc': '2.0', 'method': 'eth_blockNumber', 'params': [], 'id': 1},
        timeout=5)
    
    if response.status_code == 200:
        data = response.json()
        if 'result' in data:
            print('valid')
        elif 'error' in data:
            print(f\"error:{data['error'].get('message', 'Invalid API key')}\")
        else:
            print('error:Invalid response')
    else:
        print(f'error:HTTP {response.status_code}')
except Exception as e:
    print(f'error:Connection failed - {str(e)}')
" 2>/dev/null
}

validate_infura() {
    local api_key=$1
    
    if [ -z "$api_key" ]; then
        echo "valid"
        return
    fi
    
    python3 -c "
import requests
import sys

try:
    response = requests.post('https://mainnet.infura.io/v3/$api_key',
        json={'jsonrpc': '2.0', 'method': 'eth_blockNumber', 'params': [], 'id': 1},
        timeout=5)
    
    if response.status_code == 200:
        print('valid')
    elif response.status_code == 401:
        print('error:Invalid API key')
    else:
        print(f'error:HTTP {response.status_code}')
except Exception as e:
    print(f'error:Connection failed')
" 2>/dev/null
}

validate_etherscan() {
    local api_key=$1
    
    python3 -c "
import requests
import sys

try:
    response = requests.get(
        'https://api-$NETWORK.etherscan.io/api',
        params={
            'module': 'account',
            'action': 'balance',
            'address': '0x0000000000000000000000000000000000000000',
            'tag': 'latest',
            'apikey': '$api_key'
        },
        timeout=5
    )
    
    data = response.json()
    if data.get('status') == '1' or 'result' in data:
        print('valid')
    elif 'Invalid API Key' in str(data.get('result', '')):
        print('error:Invalid API key')
    else:
        print('error:API key validation failed')
except Exception as e:
    print(f'error:Connection failed')
" 2>/dev/null
}

validate_okx() {
    local api_key=$1
    local secret_key=$2
    local passphrase=$3
    
    python3 -c "
import requests
import hmac
import base64
from datetime import datetime
import sys

try:
    timestamp = datetime.utcnow().isoformat()[:-3] + 'Z'
    method = 'GET'
    request_path = '/api/v5/account/balance'
    
    message = timestamp + method + request_path
    mac = hmac.new(
        bytes('$secret_key', encoding='utf8'),
        bytes(message, encoding='utf8'),
        digestmod='sha256'
    )
    signature = base64.b64encode(mac.digest()).decode()
    
    headers = {
        'OK-ACCESS-KEY': '$api_key',
        'OK-ACCESS-SIGN': signature,
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': '$passphrase',
        'Content-Type': 'application/json',
        'x-simulated-trading': '1'
    }
    
    response = requests.get('https://www.okx.com/api/v5/account/balance',
        headers=headers, timeout=5)
    
    data = response.json()
    if data.get('code') == '0':
        print('valid')
    else:
        print(f\"error:{data.get('msg', 'Invalid credentials')}\")
except Exception as e:
    print(f'error:Connection failed - {str(e)}')
" 2>/dev/null
}

validate_discord() {
    local webhook_url=$1
    
    python3 -c "
import requests
import sys

try:
    response = requests.get('$webhook_url', timeout=5)
    
    if 'discord.com/api/webhooks' not in '$webhook_url':
        print('error:Invalid Discord webhook URL format')
    elif response.status_code == 200:
        print('valid')
    elif response.status_code == 401:
        print('error:Invalid webhook token')
    elif response.status_code == 404:
        print('error:Webhook not found')
    else:
        print(f'error:HTTP {response.status_code}')
except Exception as e:
    print(f'error:Connection failed')
" 2>/dev/null
}

echo "--- Ethereum Wallet Configuration ---"
while true; do
    read -sp "Enter your PRIVATE_KEY (will be hidden): " PRIVATE_KEY
    echo ""
    read -p "Enter your WALLET_ADDRESS: " WALLET_ADDRESS
    
    echo -n "Validating Ethereum keys... "
    VALIDATION=$(validate_ethereum_key "$PRIVATE_KEY" "$WALLET_ADDRESS")
    
    if [[ "$VALIDATION" == "valid" ]]; then
        echo "✅"
        break
    else
        ERROR_MSG=$(echo "$VALIDATION" | sed 's/error://')
        echo "❌"
        echo "Error: $ERROR_MSG"
        echo "Please try again."
        echo ""
    fi
done

echo ""
echo "--- Alchemy API Configuration ---"
while true; do
    read -p "Enter ALCHEMY_API_KEY: " ALCHEMY_API_KEY
    
    echo -n "Testing Alchemy connection... "
    VALIDATION=$(validate_alchemy "$ALCHEMY_API_KEY")
    
    if [[ "$VALIDATION" == "valid" ]]; then
        echo "✅"
        break
    else
        ERROR_MSG=$(echo "$VALIDATION" | sed 's/error://')
        echo "❌"
        echo "Error: $ERROR_MSG"
        echo "Please check your API key and try again."
        echo ""
    fi
done

echo ""
echo "--- Infura API Configuration (Optional) ---"
read -p "Enter INFURA_API_KEY (press enter to skip): " INFURA_API_KEY

if [ ! -z "$INFURA_API_KEY" ]; then
    echo -n "Testing Infura connection... "
    VALIDATION=$(validate_infura "$INFURA_API_KEY")
    
    if [[ "$VALIDATION" == "valid" ]]; then
        echo "✅"
    else
        ERROR_MSG=$(echo "$VALIDATION" | sed 's/error://')
        echo "⚠️  Warning: $ERROR_MSG (continuing without Infura)"
        INFURA_API_KEY=""
    fi
fi

echo ""
echo "--- Etherscan API Configuration ---"
while true; do
    read -p "Enter ETHERSCAN_API_KEY: " ETHERSCAN_API_KEY
    
    echo -n "Testing Etherscan API... "
    VALIDATION=$(validate_etherscan "$ETHERSCAN_API_KEY")
    
    if [[ "$VALIDATION" == "valid" ]]; then
        echo "✅"
        break
    else
        ERROR_MSG=$(echo "$VALIDATION" | sed 's/error://')
        echo "❌"
        echo "Error: $ERROR_MSG"
        echo "Get your API key from: https://etherscan.io/apis"
        echo ""
    fi
done

echo ""
echo "--- OKX Testnet Configuration ---"
echo "Note: Get testnet API keys from https://www.okx.com/testnet"
while true; do
    read -p "Enter OKX_API_KEY: " OKX_API_KEY
    read -sp "Enter OKX_SECRET_KEY (will be hidden): " OKX_SECRET_KEY
    echo ""
    read -p "Enter OKX_PASSPHRASE: " OKX_PASSPHRASE
    
    echo -n "Testing OKX API connection... "
    VALIDATION=$(validate_okx "$OKX_API_KEY" "$OKX_SECRET_KEY" "$OKX_PASSPHRASE")
    
    if [[ "$VALIDATION" == "valid" ]]; then
        echo "✅"
        break
    else
        ERROR_MSG=$(echo "$VALIDATION" | sed 's/error://')
        echo "❌"
        echo "Error: $ERROR_MSG"
        echo "Please check your OKX testnet credentials and try again."
        echo "Make sure you're using TESTNET API keys, not mainnet!"
        echo ""
    fi
done

echo ""
echo "--- Discord Webhook Configuration ---"
while true; do
    read -p "Enter DISCORD_WEBHOOK_URL: " DISCORD_WEBHOOK_URL
    
    echo -n "Testing Discord webhook... "
    VALIDATION=$(validate_discord "$DISCORD_WEBHOOK_URL")
    
    if [[ "$VALIDATION" == "valid" ]]; then
        echo "✅"
        
        echo -n "Sending test notification... "
        python3 -c "
import requests
requests.post('$DISCORD_WEBHOOK_URL', json={
    'content': '✅ DeFi Bot testnet setup successful!',
    'embeds': [{
        'title': 'Configuration Test',
        'description': 'Your Discord notifications are working correctly.',
        'color': 0x00ff00,
        'fields': [
            {'name': 'Network', 'value': '$NETWORK', 'inline': True},
            {'name': 'Chain ID', 'value': '$CHAIN_ID', 'inline': True}
        ]
    }]
})
print('✅')
" 2>/dev/null
        break
    else
        ERROR_MSG=$(echo "$VALIDATION" | sed 's/error://')
        echo "❌"
        echo "Error: $ERROR_MSG"
        echo "Discord webhook format: https://discord.com/api/webhooks/..."
        echo ""
    fi
done

echo ""
echo "--- Trading Parameters ---"
read -p "Enter MAX_GAS_PRICE_GWEI (default: 100): " MAX_GAS_PRICE_GWEI
MAX_GAS_PRICE_GWEI=${MAX_GAS_PRICE_GWEI:-100}

read -p "Enter MIN_PROFIT_USD (default: 10): " MIN_PROFIT_USD
MIN_PROFIT_USD=${MIN_PROFIT_USD:-10}

read -p "Enter MAX_POSITION_SIZE_ETH (default: 0.1): " MAX_POSITION_SIZE_ETH
MAX_POSITION_SIZE_ETH=${MAX_POSITION_SIZE_ETH:-0.1}

read -p "Enter SLIPPAGE_TOLERANCE (default: 0.03): " SLIPPAGE_TOLERANCE
SLIPPAGE_TOLERANCE=${SLIPPAGE_TOLERANCE:-0.03}

export PRIVATE_KEY
export WALLET_ADDRESS
export ALCHEMY_API_KEY
export INFURA_API_KEY
export ETHERSCAN_API_KEY
export OKX_API_KEY
export OKX_SECRET_KEY
export OKX_PASSPHRASE
export DISCORD_WEBHOOK_URL
export MAX_GAS_PRICE_GWEI
export MIN_PROFIT_USD
export MAX_POSITION_SIZE_ETH
export SLIPPAGE_TOLERANCE
export NETWORK
export CHAIN_ID
export RPC_BASE
export EXPLORER

cat > .env.testnet << EOF
NETWORK=$NETWORK
CHAIN_ID=$CHAIN_ID

PRIVATE_KEY=$PRIVATE_KEY
WALLET_ADDRESS=$WALLET_ADDRESS

ALCHEMY_API_KEY=$ALCHEMY_API_KEY
INFURA_API_KEY=$INFURA_API_KEY
ETHERSCAN_API_KEY=$ETHERSCAN_API_KEY

OKX_API_KEY=$OKX_API_KEY
OKX_SECRET_KEY=$OKX_SECRET_KEY
OKX_PASSPHRASE=$OKX_PASSPHRASE

DISCORD_WEBHOOK_URL=$DISCORD_WEBHOOK_URL

FLASHLOAN_CONTRACT_ADDRESS=
MULTICALL_CONTRACT_ADDRESS=

MAX_GAS_PRICE_GWEI=$MAX_GAS_PRICE_GWEI
MIN_PROFIT_USD=$MIN_PROFIT_USD
MAX_POSITION_SIZE_ETH=$MAX_POSITION_SIZE_ETH
SLIPPAGE_TOLERANCE=$SLIPPAGE_TOLERANCE

MAINNET_RPC=${RPC_BASE}
ARBITRUM_RPC=${RPC_BASE}
OPTIMISM_RPC=${RPC_BASE}
BASE_RPC=${RPC_BASE}
EOF

echo ""
echo "✅ All API keys validated successfully!"
echo "✅ Testnet configuration saved to .env.testnet"
echo ""

TESTNET_TOKENS_FILE="testnet_tokens.json"
cat > $TESTNET_TOKENS_FILE << EOF
{
  "$NETWORK": {
    "WETH": "0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14",
    "USDC": "0x94a9D9AC8a22534E3FaCa9F4e7F2E2cf85d5E4C8",
    "USDT": "0xaA8E23Fb1079EA71e0a56F48a2aA51851D8433D0",
    "DAI": "0xFF34B3d4Aee8ddCd6F9AFFFB6Fe49bD371b8a357",
    "WBTC": "0x29f2D40B0605204364af54EC677bD022dA425d03"
  }
}
EOF

echo "✅ Testnet token addresses saved to $TESTNET_TOKENS_FILE"
echo ""

FAUCET_URLS_FILE="testnet_faucets.txt"
cat > $FAUCET_URLS_FILE << EOF
====================================
    Testnet Faucets for $NETWORK    
====================================

Sepolia ETH Faucets:
- https://sepoliafaucet.com/
- https://www.alchemy.com/faucets/ethereum-sepolia
- https://faucet.quicknode.com/ethereum/sepolia

Arbitrum Sepolia:
- https://faucet.quicknode.com/arbitrum/sepolia

Optimism Sepolia:
- https://faucet.quicknode.com/optimism/sepolia

Base Sepolia:
- https://faucet.quicknode.com/base/sepolia

Test Token Faucets:
- Uniswap Testnet: https://app.uniswap.org/swap (use testnet mode)
- AAVE Testnet: https://staging.aave.com/faucet/

OKX Testnet:
- https://www.okx.com/testnet
EOF

echo "✅ Faucet URLs saved to $FAUCET_URLS_FILE"
echo ""

echo "======================================"
echo "      API Connection Summary          "
echo "======================================"
echo "✅ Ethereum Wallet:  Connected"
echo "✅ Alchemy RPC:      Connected to $NETWORK"
if [ ! -z "$INFURA_API_KEY" ]; then
    echo "✅ Infura RPC:       Connected (backup)"
else
    echo "⚠️  Infura RPC:       Not configured"
fi
echo "✅ Etherscan API:    Connected"
echo "✅ OKX Testnet:      Connected"
echo "✅ Discord Webhook:  Connected & Tested"
echo ""

echo "======================================"
echo "      Checking Python Environment     "
echo "======================================"
echo ""

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed"
    exit 1
fi

echo "✅ pip3 found"

echo ""
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

echo ""
echo "======================================"
echo "     Final Network Verification       "
echo "======================================"
echo ""

echo -n "Getting wallet balance... "
BALANCE=$(python3 -c "
from web3 import Web3
w3 = Web3(Web3.HTTPProvider('${RPC_BASE}${ALCHEMY_API_KEY}'))
balance = w3.eth.get_balance('${WALLET_ADDRESS}')
print(f'{Web3.from_wei(balance, \"ether\"):.4f} ETH')
" 2>/dev/null)

echo "$BALANCE"

if [[ "$BALANCE" == "0.0000 ETH" ]]; then
    echo ""
    echo "⚠️  Warning: Your wallet has no testnet ETH!"
    echo "   Please get testnet ETH from faucets listed in $FAUCET_URLS_FILE"
fi

echo ""
echo "======================================"
echo "        Next Steps                    "
echo "======================================"
echo ""
echo "1. Get testnet ETH from faucets (see $FAUCET_URLS_FILE)"
echo "2. Deploy contracts with: ./deploy_contracts.sh"
echo "3. Run the bot with: ./run_testnet.sh"
echo ""
echo "⚠️  IMPORTANT: Environment variables are set for this session only."
echo "   To persist them, run: source setup_testnet.sh"
echo ""
echo "✅ Testnet setup complete with all validations passed!"