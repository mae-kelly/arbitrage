#!/bin/bash
echo "🧪 Testing production system..."

export RUST_LOG=info
export PRIVATE_KEY=0x0000000000000000000000000000000000000000000000000000000000000001

echo "Testing Binance connection..."
cargo test test_binance_connection

echo "Testing Uniswap connection..."
cargo test test_uniswap_connection

echo "Testing flash loan execution..."
cargo test test_flash_loan_execution

echo "Testing cross-chain bridge..."
cargo test test_cross_chain_bridge

echo "Testing risk management..."
cargo test test_risk_management

echo "✅ All tests completed"
