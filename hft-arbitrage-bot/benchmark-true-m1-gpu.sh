#!/bin/bash

echo "⚡ TRUE M1 GPU PERFORMANCE BENCHMARK"
echo "==================================="

# Build if needed
if [ ! -f "./target/aarch64-apple-darwin/release/true-m1-gpu-arbitrage-bot" ]; then
    echo "🔨 Building for benchmark..."
    ./build-true-m1-gpu.sh
fi

echo ""
echo "🧪 COMPREHENSIVE GPU PERFORMANCE TESTS"
echo ""

# Enable Metal performance monitoring
export MTL_HUD_ENABLED=1
export METAL_PERFORMANCE_HUD=1
export MTL_CAPTURE_ENABLED=1

BINARY="./target/aarch64-apple-darwin/release/true-m1-gpu-arbitrage-bot"

echo "Test 1: GPU Scan Speed"
echo "---------------------"
echo "Measuring GPU arbitrage scan performance..."
echo "Target: <10μs per complete scan"
echo ""

time timeout 30s "$BINARY" --gpu-benchmark-scan 2>/dev/null || true

echo ""
echo "Test 2: GPU Memory Bandwidth"
echo "---------------------------"
echo "Measuring Metal GPU memory throughput..."
echo "Expected: >400 GB/s on M1"
echo ""

time timeout 15s "$BINARY" --gpu-benchmark-memory 2>/dev/null || true

echo ""
echo "Test 3: GPU Utilization"
echo "----------------------"
echo "Measuring GPU compute core utilization..."
echo "Target: >80% utilization"
echo ""

time timeout 20s "$BINARY" --gpu-benchmark-utilization 2>/dev/null || true

echo ""
echo "Test 4: Power Efficiency"
echo "-----------------------"
echo "Measuring power consumption during GPU compute..."
echo "Expected: 8-20W for M1 GPU"
echo ""

# Monitor power usage
powermetrics -n 1 -i 1000 --samplers gpu_power | grep "GPU Power" &
POWER_PID=$!
timeout 10s "$BINARY" --gpu-benchmark-power 2>/dev/null || true
kill $POWER_PID 2>/dev/null || true

echo ""
echo "Test 5: Concurrent GPU Operations"
echo "--------------------------------"
echo "Testing multiple simultaneous GPU kernels..."
echo "Target: Linear scaling with workload"
echo ""

time timeout 25s "$BINARY" --gpu-benchmark-concurrent 2>/dev/null || true

echo ""
echo "🎯 BENCHMARK SUMMARY"
echo "==================="
echo ""
echo "Expected M1 GPU Results:"
echo "• Scan time: 5-15μs (GPU) vs 50-200μs (CPU)"
echo "• Memory bandwidth: 400+ GB/s"
echo "• GPU utilization: 80-95%"
echo "• Power efficiency: 10-20W total system"
echo "• Concurrent scaling: Near-linear"
echo ""
echo "If results meet targets: TRUE GPU acceleration working!"
echo "If results are slow: Check Metal framework installation"
