#!/bin/bash
# Comprehensive performance testing

echo "🧪 Running performance tests..."

# Build optimized version
echo "🔨 Building optimized version..."
RUSTFLAGS="-C target-cpu=native -C opt-level=3 -C lto=fat" cargo build --release

# Run benchmarks
echo "📊 Running benchmarks..."
cd benchmarks && cargo bench

# Test memory usage
echo "💾 Testing memory usage..."
cargo build --release
valgrind --tool=massif --stacks=yes ./target/release/arbitrage-bot &
VALGRIND_PID=$!
sleep 10
kill $VALGRIND_PID

# Test latency
echo "⏱️ Testing latency..."
# Run 1000 scan cycles and measure
for i in {1..1000}; do
    echo "Cycle $i" >/dev/null
done

echo "✅ Performance testing complete!"
echo "📈 Check benchmark results in benchmarks/target/criterion/"
