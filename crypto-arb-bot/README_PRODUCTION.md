# 🚀 Production Arbitrage Bot

## Quick Start
1. `cp .env.example .env` and configure
2. `./scripts/production_start.sh`
3. Monitor at http://localhost:3000

## Requirements
- $50k+ starting capital
- Mainnet RPC endpoints (Alchemy/Infura)
- Exchange API keys
- 24/7 server monitoring

## Risk Management
- Max position: $100k per trade
- Daily loss limit: $5k
- Emergency stop: `./scripts/emergency_stop.sh`

## Monitoring
- Grafana dashboard: Port 3000
- Prometheus metrics: Port 9090
- Bot API: Port 3030/stats
- Slack alerts configured

## Profit Expectations
- Target: 0.1-0.5% per trade
- Frequency: 10-50 trades/day
- Monthly return: 5-15%
- Gas costs: $50-200/trade on L1

## Emergency Procedures
1. Stop bot: `docker-compose stop arbitrage-bot`
2. Withdraw funds: `./scripts/emergency_stop.sh`
3. Check logs: `docker-compose logs arbitrage-bot`

⚠️ NEVER RUN ON MAINNET WITHOUT EXTENSIVE TESTNET TESTING
