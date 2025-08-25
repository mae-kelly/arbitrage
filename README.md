# Quantum Arbitrage Bot

Advanced ML-powered DEX arbitrage bot utilizing flash loans for capital-efficient trading.

## Features

- Multi-DEX arbitrage detection (Uniswap V2/V3, SushiSwap, Balancer, Curve)
- Flash loan integration (Aave, Balancer, Uniswap V3)
- Neural network price prediction using M1 GPU acceleration
- Rust-based high-performance execution engine
- Real-time mempool monitoring
- Automatic profit calculation with gas optimization

## Architecture

- **Rust Core**: CPU-optimized arbitrage detection and trade execution
- **Python ML**: GPU-accelerated neural network for opportunity scoring
- **Hybrid Processing**: Rust handles real-time operations, Python handles ML inference

## Setup

1. Clone repository
2. Copy `.env.example` to `.env` and add your API keys
3. Build and run with Docker:

```bash
docker-compose up -d
```

## Operating Modes

### Test Mode (Default)
- Simulates trades without executing
- Uses forked mainnet for realistic testing
- Logs all opportunities and expected profits

### Production Mode
- Executes real trades on mainnet
- Requires funded wallet
- Automatic flash loan selection

## Configuration

Set in `.env`:
- `MODE`: "test" or "production"
- `MIN_PROFIT_USD`: Minimum profit threshold
- `MAX_GAS_GWEI`: Maximum gas price willing to pay
- Flash loan providers: Enable/disable specific providers

## ML Model

The neural network uses:
- 10-layer deep architecture with attention mechanisms
- LSTM + GRU for temporal pattern recognition
- Trained on historical arbitrage data
- M1 GPU acceleration via Metal Performance Shaders

## Database Schema

PostgreSQL stores:
- Trade history and performance metrics
- Discovered opportunities
- ML training data
- Gas price history

## Monitoring

- Prometheus metrics at `http://localhost:9090`
- Grafana dashboards at `http://localhost:3000`

## Safety Features

- Position limits and exposure management
- Circuit breakers for anomaly detection
- Automatic gas price optimization
- Slippage protection

## Legal Compliance

This bot performs legal DEX arbitrage using flash loans. Users must:
- Comply with local regulations
- Report profits for tax purposes
- Respect exchange terms of service

## Performance

- Sub-100ms opportunity detection
- Parallel processing across multiple DEXs
- Optimized for high-frequency trading
- Memory-efficient with zero-copy operations

## Development

Run tests:
```bash
cargo test
python -m pytest ml/tests
```

Train ML model:
```bash
python ml/trainer.py
```

## License

Proprietary - All rights reserved