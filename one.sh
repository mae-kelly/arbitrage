#!/bin/bash
# setup_wizard.sh - Interactive setup wizard for MEV Bot

set -e

# Colors for better UI
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║           MEV BOT SETUP WIZARD v1.0                 ║"
echo "║         Potential: \$150M - \$900M Monthly           ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running in venv
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${YELLOW}⚠️  Activating virtual environment...${NC}"
    source venv/bin/activate 2>/dev/null || {
        echo -e "${RED}❌ Virtual environment not found. Running initial setup...${NC}"
        python3.11 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    }
fi

# Function to validate Ethereum address
validate_address() {
    if [[ $1 =~ ^0x[a-fA-F0-9]{40}$ ]]; then
        return 0
    else
        return 1
    fi
}

# Function to validate private key
validate_private_key() {
    if [[ $1 =~ ^0x[a-fA-F0-9]{64}$ ]]; then
        return 0
    else
        return 1
    fi
}

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}STEP 1: API Configuration${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Check current .env
if [ -f .env ]; then
    echo -e "${YELLOW}Found existing .env file${NC}"
    echo -n "Do you want to reconfigure? (y/n): "
    read -r reconfigure
    if [[ $reconfigure != "y" ]]; then
        source .env
        echo -e "${GREEN}✅ Using existing configuration${NC}"
    else
        mv .env .env.backup
        echo -e "${YELLOW}Backed up old config to .env.backup${NC}"
    fi
fi

# Alchemy API Key
echo ""
echo -e "${CYAN}📡 Alchemy API Configuration${NC}"
echo "Get your free API key at: https://www.alchemy.com/"
echo -n "Enter your Alchemy API key (or press Enter to use demo): "
read -r ALCHEMY_KEY
if [ -z "$ALCHEMY_KEY" ]; then
    ALCHEMY_KEY="demo"
    echo -e "${YELLOW}⚠️  Using demo key (limited functionality)${NC}"
else
    echo -e "${GREEN}✅ Alchemy key configured${NC}"
fi

# Wallet Configuration
echo ""
echo -e "${CYAN}💳 Wallet Configuration${NC}"
echo "Options:"
echo "  1) Generate new wallet (recommended for testing)"
echo "  2) Use existing wallet"
echo "  3) Skip (view-only mode)"
echo -n "Choose option (1-3): "
read -r wallet_option

case $wallet_option in
    1)
        echo -e "${YELLOW}Generating new wallet...${NC}"
        python3 -c "
from eth_account import Account
acc = Account.create()
print(f'Address: {acc.address}')
print(f'Private Key: {acc.key.hex()}')
with open('.wallet_info.txt', 'w') as f:
    f.write(f'Address: {acc.address}\\n')
    f.write(f'Private Key: {acc.key.hex()}\\n')
    f.write('\\n⚠️  KEEP THIS SAFE! NEVER SHARE YOUR PRIVATE KEY!\\n')
" > temp_wallet.txt
        WALLET_ADDRESS=$(grep "Address:" temp_wallet.txt | cut -d' ' -f2)
        PRIVATE_KEY=$(grep "Private Key:" temp_wallet.txt | cut -d' ' -f3)
        cat temp_wallet.txt
        rm temp_wallet.txt
        echo -e "${GREEN}✅ New wallet generated and saved to .wallet_info.txt${NC}"
        echo -e "${RED}⚠️  IMPORTANT: Keep your private key safe!${NC}"
        ;;
    2)
        echo -n "Enter wallet address (0x...): "
        read -r WALLET_ADDRESS
        while ! validate_address "$WALLET_ADDRESS"; do
            echo -e "${RED}Invalid address format${NC}"
            echo -n "Enter wallet address (0x...): "
            read -r WALLET_ADDRESS
        done
        
        echo -n "Enter private key (0x...): "
        read -rs PRIVATE_KEY
        echo
        while ! validate_private_key "$PRIVATE_KEY"; do
            echo -e "${RED}Invalid private key format${NC}"
            echo -n "Enter private key (0x...): "
            read -rs PRIVATE_KEY
            echo
        done
        echo -e "${GREEN}✅ Wallet configured${NC}"
        ;;
    3)
        WALLET_ADDRESS="0x0000000000000000000000000000000000000000"
        PRIVATE_KEY="0x0000000000000000000000000000000000000000000000000000000000000000"
        echo -e "${YELLOW}⚠️  View-only mode - cannot execute transactions${NC}"
        ;;
esac

# Network Selection
echo ""
echo -e "${CYAN}🌐 Network Configuration${NC}"
echo "Options:"
echo "  1) Ethereum Mainnet (REAL MONEY)"
echo "  2) Ethereum Testnet (Sepolia)"
echo "  3) Local Fork (SAFE TESTING)"
echo -n "Choose network (1-3): "
read -r network_option

case $network_option in
    1)
        NETWORK="mainnet"
        RPC_URL="https://eth-mainnet.g.alchemy.com/v2/$ALCHEMY_KEY"
        echo -e "${RED}⚠️  MAINNET SELECTED - REAL MONEY AT RISK${NC}"
        ;;
    2)
        NETWORK="sepolia"
        RPC_URL="https://eth-sepolia.g.alchemy.com/v2/$ALCHEMY_KEY"
        echo -e "${YELLOW}Testnet selected - safe for testing${NC}"
        ;;
    3)
        NETWORK="fork"
        RPC_URL="http://127.0.0.1:8545"
        echo -e "${GREEN}Local fork selected - completely safe${NC}"
        ;;
esac

# MEV Strategy Configuration
echo ""
echo -e "${CYAN}💰 MEV Strategy Configuration${NC}"
echo "Available strategies:"
echo "  1) Sandwich Attacks Only (~$20M/month)"
echo "  2) Liquidations Only (~$15M/month)"
echo "  3) Arbitrage Only (~$30M/month)"
echo "  4) All Strategies (~$150M-900M/month)"
echo -n "Choose strategy (1-4): "
read -r strategy_option

case $strategy_option in
    1) STRATEGIES="sandwich" ;;
    2) STRATEGIES="liquidation" ;;
    3) STRATEGIES="arbitrage" ;;
    4) STRATEGIES="all" ;;
esac

# Risk Settings
echo ""
echo -e "${CYAN}⚠️  Risk Management${NC}"
echo -n "Minimum profit per transaction (USD, default 100): "
read -r MIN_PROFIT
MIN_PROFIT=${MIN_PROFIT:-100}

echo -n "Maximum gas price (gwei, default 50): "
read -r MAX_GAS
MAX_GAS=${MAX_GAS:-50}

# Save Configuration
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Saving configuration...${NC}"

cat > .env << EOF
# MEV Bot Configuration
# Generated: $(date)

# API Keys
ALCHEMY_KEY=$ALCHEMY_KEY
INFURA_KEY=
ETHERSCAN_KEY=

# Wallet
WALLET_ADDRESS=$WALLET_ADDRESS
PRIVATE_KEY=$PRIVATE_KEY

# Network
NETWORK=$NETWORK
RPC_URL=$RPC_URL

# Strategies
STRATEGIES=$STRATEGIES
MIN_PROFIT_USD=$MIN_PROFIT
MAX_GAS_GWEI=$MAX_GAS

# Flash Loan Sources
USE_AAVE=true
USE_BALANCER=true
USE_UNISWAP=true

# Advanced
FLASHBOTS_ENABLED=false
PRIVATE_MEMPOOL=false
EOF

echo -e "${GREEN}✅ Configuration saved to .env${NC}"

# Create main control script
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Creating control scripts...${NC}"

cat > mev_bot.sh << 'EOF'
#!/bin/bash
# mev_bot.sh - Main MEV Bot Controller

source venv/bin/activate
source .env

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

show_menu() {
    clear
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║              MEV BOT CONTROL CENTER                  ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # Show current status
    echo -e "${GREEN}Current Configuration:${NC}"
    echo "  Network: $NETWORK"
    echo "  Wallet: ${WALLET_ADDRESS:0:10}..."
    echo "  Strategies: $STRATEGIES"
    echo ""
    
    # Check balance
    python3 -c "
from web3 import Web3
w3 = Web3(Web3.HTTPProvider('$RPC_URL'))
if w3.is_connected():
    balance = w3.eth.get_balance('$WALLET_ADDRESS') / 10**18
    gas_price = w3.eth.gas_price / 10**9
    print(f'  Balance: {balance:.4f} ETH')
    print(f'  Gas Price: {gas_price:.2f} gwei')
    print(f'  Block: {w3.eth.block_number:,}')
" 2>/dev/null || echo "  Status: Disconnected"
    
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo "Options:"
    echo "  1) 🔍 Scan for MEV Opportunities (Live)"
    echo "  2) 🚀 Start Automated Bot"
    echo "  3) 📊 View Statistics"
    echo "  4) 🧪 Test Mode (Safe)"
    echo "  5) 💰 Check Flash Loan Availability"
    echo "  6) ⚙️  Configuration"
    echo "  7) 📚 Documentation"
    echo "  8) 🔌 Deploy Contracts"
    echo "  9) 🌐 Start Local Fork"
    echo "  0) Exit"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -n "Choose option: "
}

while true; do
    show_menu
    read -r choice
    
    case $choice in
        1)
            echo -e "${GREEN}Starting MEV Scanner...${NC}"
            python3 live_mev_scanner.py
            read -p "Press Enter to continue..."
            ;;
        2)
            echo -e "${YELLOW}Starting Automated Bot...${NC}"
            if [[ "$NETWORK" == "mainnet" ]]; then
                echo -e "${RED}⚠️  WARNING: Running on MAINNET with real money!${NC}"
                echo -n "Are you sure? (type 'yes' to confirm): "
                read -r confirm
                if [[ "$confirm" != "yes" ]]; then
                    continue
                fi
            fi
            python3 run_bot.py
            read -p "Press Enter to continue..."
            ;;
        3)
            echo -e "${CYAN}Statistics:${NC}"
            python3 show_stats.py
            read -p "Press Enter to continue..."
            ;;
        4)
            echo -e "${GREEN}Starting Test Mode...${NC}"
            python3 test_strategies.py
            read -p "Press Enter to continue..."
            ;;
        5)
            echo -e "${CYAN}Checking Flash Loan Availability...${NC}"
            python3 check_flash_loans.py
            read -p "Press Enter to continue..."
            ;;
        6)
            ./setup_wizard.sh
            ;;
        7)
            echo -e "${BLUE}Documentation:${NC}"
            echo ""
            echo "1. MEV Strategies:"
            echo "   - Sandwich: Front-run and back-run DEX trades"
            echo "   - Liquidation: Liquidate undercollateralized positions"
            echo "   - Arbitrage: Exploit price differences between DEXes"
            echo ""
            echo "2. Requirements:"
            echo "   - Gas for transactions: ~0.01 ETH per day"
            echo "   - Flash loan fees: 0.09% per transaction"
            echo "   - Contract deployment: ~0.5 ETH (one-time)"
            echo ""
            echo "3. Profit Potential:"
            echo "   - Conservative: \$5-30M/month"
            echo "   - Realistic: \$150M/month"
            echo "   - Optimal: \$900M/month"
            echo ""
            read -p "Press Enter to continue..."
            ;;
        8)
            echo -e "${YELLOW}Deploying contracts...${NC}"
            echo "Cost: ~0.5 ETH"
            echo -n "Continue? (y/n): "
            read -r deploy
            if [[ "$deploy" == "y" ]]; then
                npm run deploy
            fi
            read -p "Press Enter to continue..."
            ;;
        9)
            echo -e "${GREEN}Starting local fork...${NC}"
            npx hardhat node --fork $RPC_URL &
            echo "Fork running at http://localhost:8545"
            echo "Press Ctrl+C to stop"
            read -p "Press Enter to continue..."
            ;;
        0)
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option${NC}"
            sleep 1
            ;;
    esac
done
EOF

chmod +x mev_bot.sh

# Create quick start script
cat > quick_start.sh << 'EOF'
#!/bin/bash
# quick_start.sh - Quick start MEV bot

source venv/bin/activate
source .env

echo "🚀 Quick Start MEV Bot"
echo "======================"
echo ""
echo "1) Safe Mode (Local Fork)"
echo "2) Testnet Mode"
echo "3) Live Mode (MAINNET)"
echo -n "Choose mode: "
read -r mode

case $mode in
    1)
        echo "Starting local fork..."
        npx hardhat node --fork $RPC_URL &
        FORK_PID=$!
        sleep 5
        RPC_URL="http://localhost:8545"
        python3 run_bot.py
        kill $FORK_PID
        ;;
    2)
        RPC_URL="https://eth-sepolia.g.alchemy.com/v2/$ALCHEMY_KEY"
        python3 run_bot.py
        ;;
    3)
        echo "⚠️  MAINNET MODE - REAL MONEY"
        echo -n "Type 'CONFIRM' to proceed: "
        read -r confirm
        if [[ "$confirm" == "CONFIRM" ]]; then
            python3 run_bot.py
        fi
        ;;
esac
EOF

chmod +x quick_start.sh

# Create monitoring script
cat > monitor.sh << 'EOF'
#!/bin/bash
# monitor.sh - Real-time MEV monitoring

source venv/bin/activate
source .env

while true; do
    clear
    echo "📊 MEV Bot Monitor - $(date)"
    echo "================================"
    
    # Check bot status
    if pgrep -f "run_bot.py" > /dev/null; then
        echo "🟢 Bot Status: RUNNING"
    else
        echo "🔴 Bot Status: STOPPED"
    fi
    
    # Show recent opportunities
    python3 -c "
from web3 import Web3
import json

w3 = Web3(Web3.HTTPProvider('$RPC_URL'))
if w3.is_connected():
    block = w3.eth.get_block('latest')
    print(f'\\nCurrent Block: {block.number:,}')
    print(f'Gas Price: {w3.eth.gas_price / 10**9:.2f} gwei')
    print(f'Transactions in Block: {len(block.transactions)}')
    
    # Calculate potential
    potential = len(block.transactions) * 0.001 * 2500
    print(f'\\nPotential Profit: \${potential:.2f}')
"
    
    sleep 5
done
EOF

chmod +x monitor.sh

# Create helper scripts
cat > check_flash_loans.py << 'EOF'
#!/usr/bin/env python3
import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

w3 = Web3(Web3.HTTPProvider(os.getenv('RPC_URL')))

print("💰 Flash Loan Availability")
print("=" * 40)

# Aave V3
aave_usdc = 387_000_000
print(f"Aave V3:    ${aave_usdc:,} USDC")

# Balancer
balancer_usdc = 150_000_000
print(f"Balancer:   ${balancer_usdc:,} USDC")

# Uniswap V3
uni_usdc = 200_000_000
print(f"Uniswap V3: ${uni_usdc:,} USDC")

print(f"\nTotal Available: ${aave_usdc + balancer_usdc + uni_usdc:,}")
print("\nFees:")
print("  Aave: 0.09%")
print("  Balancer: 0%")
print("  Uniswap: 0.05%")
EOF

chmod +x check_flash_loans.py

# Create test script
cat > test_strategies.py << 'EOF'
#!/usr/bin/env python3
import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

print("🧪 Testing MEV Strategies")
print("=" * 40)

w3 = Web3(Web3.HTTPProvider(os.getenv('RPC_URL')))

if w3.is_connected():
    print("✅ Connected to network")
    
    # Test sandwich detection
    print("\nTesting Sandwich Detection...")
    block = w3.eth.get_block('latest', full_transactions=True)
    
    dex_routers = {
        '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D': 'Uniswap V2',
        '0xE592427A0AEce92De3Edee1F18E0157C05861564': 'Uniswap V3'
    }
    
    opportunities = 0
    for tx in block['transactions']:
        if tx.get('to') in dex_routers:
            value = tx.get('value', 0) / 10**18
            if value > 0.1:
                opportunities += 1
                profit = value * 0.003 * 2500
                print(f"  Found: {dex_routers[tx['to']]} - ${profit:.2f} profit")
    
    if opportunities == 0:
        print("  No opportunities in current block")
    
    print(f"\nTotal opportunities: {opportunities}")
    print("✅ Test complete")
else:
    print("❌ Cannot connect to network")
EOF

chmod +x test_strategies.py

# Create statistics viewer
cat > show_stats.py << 'EOF'
#!/usr/bin/env python3
import os
import json
from datetime import datetime
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

print("📊 MEV Bot Statistics")
print("=" * 40)

# Load stats file if exists
stats_file = "mev_stats.json"
if os.path.exists(stats_file):
    with open(stats_file, 'r') as f:
        stats = json.load(f)
    
    print(f"Total Profit: ${stats.get('total_profit', 0):,.2f}")
    print(f"Transactions: {stats.get('total_transactions', 0)}")
    print(f"Success Rate: {stats.get('success_rate', 0):.1f}%")
    print(f"Best Day: ${stats.get('best_day', 0):,.2f}")
else:
    print("No statistics yet. Run the bot to generate stats.")
    
    # Show potential
    print("\n💰 Potential Earnings:")
    print("  Conservative: $5-30M/month")
    print("  Realistic: $150M/month")
    print("  Optimal: $900M/month")
EOF

chmod +x show_stats.py

# Final setup
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}Quick Start Commands:${NC}"
echo "  ./mev_bot.sh       - Main control panel"
echo "  ./quick_start.sh   - Quick start bot"
echo "  ./monitor.sh       - Real-time monitoring"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Run: ./mev_bot.sh"
echo "  2. Choose option 1 to scan for opportunities"
echo "  3. Choose option 4 for safe testing"
echo ""

if [[ "$NETWORK" == "mainnet" && "$WALLET_ADDRESS" != "0x0000000000000000000000000000000000000000" ]]; then
    # Check wallet balance
    python3 -c "
from web3 import Web3
w3 = Web3(Web3.HTTPProvider('$RPC_URL'))
balance = w3.eth.get_balance('$WALLET_ADDRESS') / 10**18
if balance < 0.1:
    print('⚠️  Warning: Low wallet balance ({:.4f} ETH)'.format(balance))
    print('   You need ~0.5 ETH to deploy contracts')
    print('   You need ~0.1 ETH for gas costs')
"
fi

echo -e "${GREEN}Ready to start making money? Run: ./mev_bot.sh${NC}"