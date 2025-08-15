# Realistic Arbitrage Bot

A practical cryptocurrency arbitrage bot that works with real exchange APIs.

## Features

- ✅ Real exchange integration (Coinbase, Kraken, Bitstamp)
- ✅ Proper rate limiting and error handling
- ✅ Fee-adjusted profit calculations
- ✅ Safety-first approach (no auto-trading)
- ✅ Comprehensive logging

## Quick Start

1. **Install Rust**: https://rustup.rs/

2. **Build and run**:
   ```bash
   ./build.sh
   ./run.sh
   ```

3. **Development mode**:
   ```bash
   ./dev.sh
   ```

## Configuration

Edit `.env` to customize:
- `MIN_PROFIT_PERCENT=0.3` - Minimum profit threshold
- `SCAN_INTERVAL=60` - Seconds between scans
- `RUST_LOG=info` - Logging level

## Sample Output

```
🔍 Scan #3: Fetching market data...
⚡ Scan completed in 2.1s | 12 prices | 2 opportunities

💰 Arbitrage Opportunities Found:
  1. BTC-USD | Buy: bitstamp @ $43,120.50 → Sell: coinbase @ $43,250.00
     Profit: 0.301% | Est: $1.01 on $1000 trade
  2. ETH-USD | Buy: kraken @ $2,401.25 → Sell: bitstamp @ $2,412.00
     Profit: 0.448% | Est: $1.48 on $1000 trade

🚨 MANUAL EXECUTION REQUIRED (Auto-trading disabled for safety)
```

## Legal Notice

Educational purposes only. Trading involves risk. Comply with local regulations.
