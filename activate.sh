#!/bin/bash
source arb-env/bin/activate
export PYTHONPATH="$(pwd)/src/python:$PYTHONPATH"
export RUST_LOG="lightning_arbitrage=debug"
echo "🚀 Lightning Arbitrage Environment Activated"
echo "Python Virtual Environment: $(which python)"
echo "Rust Version: $(rustc --version)"
