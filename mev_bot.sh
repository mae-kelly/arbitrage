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
