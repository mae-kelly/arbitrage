#!/bin/bash
# System optimization for ultra-low latency trading

echo "⚡ Optimizing system for ultra-low latency..."

# Check if running on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 Detected macOS - applying Apple Silicon optimizations"
    
    # Disable CPU frequency scaling
    sudo pmset -a powernap 0
    sudo pmset -a womp 0
    sudo pmset -a ring 0
    sudo pmset -a standby 0
    sudo pmset -a sleep 0
    sudo pmset -a hibernatemode 0
    
    # Set performance mode
    sudo pmset -a perfbias 0
    
    echo "✅ macOS power management optimized"
else
    echo "🐧 Detected Linux - applying general optimizations"
    
    # Set CPU governor to performance
    echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
    
    # Disable CPU idle states
    sudo cpupower idle-set -D 0
    
    # Set kernel parameters for low latency
    echo 'kernel.sched_rt_runtime_us = -1' | sudo tee -a /etc/sysctl.conf
    echo 'kernel.sched_rt_period_us = 1000000' | sudo tee -a /etc/sysctl.conf
    echo 'net.core.busy_read = 50' | sudo tee -a /etc/sysctl.conf
    echo 'net.core.busy_poll = 50' | sudo tee -a /etc/sysctl.conf
    
    sudo sysctl -p
    
    echo "✅ Linux system optimized"
fi

# Rust optimization flags
export RUSTFLAGS="-C target-cpu=native -C opt-level=3 -C lto=fat -C codegen-units=1"

# Set real-time priority (if supported)
ulimit -r unlimited 2>/dev/null || echo "⚠️  Could not set unlimited real-time priority"

echo "✅ System optimization complete!"
echo "📝 Rebuild with: RUSTFLAGS=\"-C target-cpu=native -C opt-level=3 -C lto=fat\" cargo build --release"
