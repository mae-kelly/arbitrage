#!/bin/bash

export RUST_LOG=info
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

echo "Starting Billion Dollar Bot..."

echo "Compiling Rust components..."
cd rust
cargo build --release
cd ..

echo "Starting Rust executors..."
./rust/target/release/mempool_stream &
MEMPOOL_PID=$!

./rust/target/release/atomic_executor &
EXECUTOR_PID=$!

echo "Starting Python engine..."
python3 core/engine.py &
ENGINE_PID=$!

echo "Bot is running!"
echo "Mempool Monitor PID: $MEMPOOL_PID"
echo "Atomic Executor PID: $EXECUTOR_PID"
echo "Main Engine PID: $ENGINE_PID"

trap "kill $MEMPOOL_PID $EXECUTOR_PID $ENGINE_PID" EXIT

wait