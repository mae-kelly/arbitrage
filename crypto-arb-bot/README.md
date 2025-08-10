# Advanced Crypto Arbitrage Bot

## Features
- Flash loan arbitrage on Ethereum L1 and L2s
- Cross-chain arbitrage with bridge monitoring
- M1 GPU-optimized ML for price prediction
- Mempool monitoring and MEV protection via Flashbots
- Real-time WebSocket feeds from multiple DEXs
- Reinforcement learning for strategy optimization

## Setup
1. Configure your API keys in `.env`
2. Run `./setup.sh` to install dependencies
3. Run `./generate_contracts.sh` to create smart contracts
4. Run `./generate_rust_core.sh` for Rust components
5. Run `./generate_scanner.sh` for scanner modules
6. Run `./generate_rust_ml_feeds.sh` for ML and feeds
7. Run `./generate_ml.sh` for Python ML components
8. Run `./generate_typescript.sh` for monitoring scripts

## Running
```bash
./start.sh
```

## Architecture
- **Rust Core**: Ultra-low latency execution engine
- **ML Engine**: M1-optimized neural networks for prediction
- **Smart Contracts**: Flash loan and cross-chain arbitrage
- **TypeScript Monitor**: Real-time opportunity detection
- **WebSocket Feeds**: Direct DEX connections

## Configuration
Edit files in `config/` directory:
- `chains.json`: Blockchain RPC endpoints
- `dexs.json`: DEX contract addresses
- `strategies.json`: Trading parameters

## Performance
- Sub-millisecond execution latency
- GPU-accelerated ML inference
- Parallel multi-chain monitoring
- Flash loan capital efficiency

## Security
- Private transaction submission via Flashbots
- Sandboxed contract execution
- Rate limiting and circuit breakers
- Secure key management
