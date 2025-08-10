#!/bin/bash

echo "🧹 Cleaning up repository - removing unneeded files..."

# Remove demo/mock projects
echo "Removing demo projects..."
rm -rf multi-layer-arbitrage/
rm -rf real-arbitrage-bot/
rm -rf src/

# Remove incomplete/placeholder modules from crypto-arb-bot
echo "Cleaning crypto-arb-bot structure..."
cd crypto-arb-bot

# Remove old/incomplete core modules
rm -rf core/src/scanner/
rm -rf core/src/ml/predictor.rs
rm -rf core/src/ml/reinforcement.rs
rm -rf core/src/feeds/

# Remove placeholder Python ML (we have production Rust now)
rm -rf ml/

# Remove TypeScript scripts (replaced with Rust production code)
rm -rf scripts/monitor.ts
rm -rf scripts/backtest.ts
rm -rf scripts/monitor_advanced.ts

# Remove shell enhancement scripts (they were just adding more placeholders)
rm -f enhance_*.sh
rm -f generate_*.sh

# Remove incomplete contract interfaces
rm -rf contracts/interfaces/

# Remove old configuration files
rm -f config/production.json
rm -f config/strategies.json

# Clean up build artifacts
rm -rf target/
rm -rf node_modules/
rm -f Cargo.lock
rm -f package-lock.json

# Remove Docker files (we have prod docker-compose now)
rm -f Dockerfile
rm -f docker-compose.yml

# Remove old shell scripts
rm -f start.sh

# Keep only essential files
echo "Keeping only production-ready files:"
echo "✓ core/src/exchanges/ (production connectors)"
echo "✓ core/src/bridges/ (real bridge integration)"
echo "✓ core/src/execution/ (production executor)"
echo "✓ core/src/risk/ (risk management)"
echo "✓ core/src/monitoring/ (alerts & metrics)"
echo "✓ contracts/ProductionFlashLoan.sol"
echo "✓ scripts/production_start.sh"
echo "✓ scripts/emergency_stop.sh"
echo "✓ docker-compose.prod.yml"
echo "✓ monitoring/ (Grafana/Prometheus config)"

cd ..

# Create clean directory structure summary
echo ""
echo "📁 Final clean repository structure:"
echo "crypto-arb-bot/"
echo "├── core/"
echo "│   ├── src/"
echo "│   │   ├── exchanges/     # Real exchange connectors"
echo "│   │   ├── bridges/       # Cross-chain bridges"
echo "│   │   ├── execution/     # Production executor"
echo "│   │   ├── risk/          # Risk management"
echo "│   │   ├── monitoring/    # Alerts & metrics"
echo "│   │   ├── tests/         # Integration tests"
echo "│   │   ├── main.rs        # Production main"
echo "│   │   └── lib.rs"
echo "│   └── Cargo.toml"
echo "├── contracts/"
echo "│   └── ProductionFlashLoan.sol"
echo "├── scripts/"
echo "│   ├── production_start.sh"
echo "│   ├── emergency_stop.sh"
echo "│   └── emergency_withdraw.ts"
echo "├── monitoring/"
echo "│   ├── prometheus.yml"
echo "│   └── grafana-dashboard.json"
echo "├── docker-compose.prod.yml"
echo "├── hardhat.config.ts"
echo "├── .env.example"
echo "└── README_PRODUCTION.md"

echo ""
echo "✅ Repository cleaned! Only production-ready arbitrage system remains."
echo ""
echo "🚀 Ready for production deployment:"
echo "1. Configure .env file"
echo "2. Test on Goerli: npx hardhat run scripts/deploy.ts --network goerli"
echo "3. Run tests: ./test_production.sh"
echo "4. Deploy production: ./scripts/production_start.sh"