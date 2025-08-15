#!/bin/bash
echo "📊 Adding Advanced Monitoring and Analytics"

mkdir -p monitoring/
mkdir -p analytics/
mkdir -p dashboards/

# Create performance monitoring
cat > src/monitoring.rs << 'MONEOF'
// ADVANCED PERFORMANCE MONITORING

use std::sync::Arc;
use std::sync::atomic::{AtomicU64, AtomicF64, Ordering};
use std::collections::HashMap;
use parking_lot::RwLock;
use tokio::time::{Duration, Instant};

pub struct PerformanceMonitor {
    // Core metrics
    total_scans: AtomicU64,
    successful_arbitrages: AtomicU64,
    total_profit: AtomicF64,
    total_volume: AtomicF64,
    
    // Timing metrics
    scan_times: Arc<RwLock<Vec<u64>>>,
    execution_times: Arc<RwLock<Vec<u64>>>,
    
    // Exchange-specific metrics
    exchange_performance: Arc<RwLock<HashMap<String, ExchangeMetrics>>>,
    
    // ML metrics
    prediction_accuracy: Arc<RwLock<HashMap<String, f64>>>,
    
    start_time: Instant,
}

#[derive(Debug, Clone)]
pub struct ExchangeMetrics {
    pub response_time_avg: f64,
    pub success_rate: f64,
    pub volume_24h: f64,
    pub arbitrage_opportunities: u64,
}

impl PerformanceMonitor {
    pub fn new() -> Self {
        Self {
            total_scans: AtomicU64::new(0),
            successful_arbitrages: AtomicU64::new(0),
            total_profit: AtomicF64::new(0.0),
            total_volume: AtomicF64::new(0.0),
            scan_times: Arc::new(RwLock::new(Vec::new())),
            execution_times: Arc::new(RwLock::new(Vec::new())),
            exchange_performance: Arc::new(RwLock::new(HashMap::new())),
            prediction_accuracy: Arc::new(RwLock::new(HashMap::new())),
            start_time: Instant::now(),
        }
    }
    
    pub fn record_scan(&self, duration_ns: u64) {
        self.total_scans.fetch_add(1, Ordering::Relaxed);
        let mut scan_times = self.scan_times.write();
        scan_times.push(duration_ns);
        if scan_times.len() > 10000 {
            scan_times.drain(0..scan_times.len() - 10000);
        }
    }
    
    pub fn record_arbitrage(&self, profit: f64, volume: f64) {
        self.successful_arbitrages.fetch_add(1, Ordering::Relaxed);
        
        // Atomic float operations using bit manipulation
        let current_profit = f64::from_bits(self.total_profit.load(Ordering::Relaxed));
        self.total_profit.store((current_profit + profit).to_bits(), Ordering::Relaxed);
        
        let current_volume = f64::from_bits(self.total_volume.load(Ordering::Relaxed));
        self.total_volume.store((current_volume + volume).to_bits(), Ordering::Relaxed);
    }
    
    pub fn get_performance_summary(&self) -> PerformanceSummary {
        let scan_times = self.scan_times.read();
        let avg_scan_time = if !scan_times.is_empty() {
            scan_times.iter().sum::<u64>() / scan_times.len() as u64
        } else {
            0
        };
        
        let runtime = self.start_time.elapsed();
        let scans = self.total_scans.load(Ordering::Relaxed);
        let arbitrages = self.successful_arbitrages.load(Ordering::Relaxed);
        let profit = f64::from_bits(self.total_profit.load(Ordering::Relaxed));
        let volume = f64::from_bits(self.total_volume.load(Ordering::Relaxed));
        
        PerformanceSummary {
            runtime_seconds: runtime.as_secs(),
            total_scans: scans,
            successful_arbitrages: arbitrages,
            total_profit: profit,
            total_volume: volume,
            avg_scan_time_ns: avg_scan_time,
            scans_per_second: scans as f64 / runtime.as_secs_f64(),
            arbitrage_success_rate: if scans > 0 { arbitrages as f64 / scans as f64 } else { 0.0 },
            profit_per_arbitrage: if arbitrages > 0 { profit / arbitrages as f64 } else { 0.0 },
        }
    }
}

#[derive(Debug)]
pub struct PerformanceSummary {
    pub runtime_seconds: u64,
    pub total_scans: u64,
    pub successful_arbitrages: u64,
    pub total_profit: f64,
    pub total_volume: f64,
    pub avg_scan_time_ns: u64,
    pub scans_per_second: f64,
    pub arbitrage_success_rate: f64,
    pub profit_per_arbitrage: f64,
}

// Global performance monitor
lazy_static::lazy_static! {
    pub static ref PERFORMANCE_MONITOR: Arc<PerformanceMonitor> = Arc::new(PerformanceMonitor::new());
}
MONEOF

echo "✅ Performance monitoring created"

# Create real-time dashboard
cat > dashboards/realtime_dashboard.html << 'DASHEOF'
<!DOCTYPE html>
<html>
<head>
    <title>Ultra-Fast Arbitrage Bot Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { font-family: 'Courier New', monospace; background: #000; color: #00ff00; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .metric-card { background: #111; border: 1px solid #00ff00; padding: 15px; margin: 10px; border-radius: 5px; }
        .metric-value { font-size: 24px; font-weight: bold; color: #00ffff; }
        .metric-label { font-size: 14px; color: #888; }
        h1 { text-align: center; color: #00ffff; }
        .status-good { color: #00ff00; }
        .status-warning { color: #ffff00; }
        .status-error { color: #ff0000; }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ ULTRA-FAST ARBITRAGE BOT DASHBOARD ⚡</h1>
        
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;">
            <div class="metric-card">
                <div class="metric-label">Scan Speed</div>
                <div class="metric-value" id="scan-speed">--μs</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Scans/Second</div>
                <div class="metric-value" id="scans-per-sec">--</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Profit</div>
                <div class="metric-value" id="total-profit">$--</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Success Rate</div>
                <div class="metric-value" id="success-rate">--%</div>
            </div>
        </div>
        
        <div id="profit-chart" style="height: 400px; margin: 20px 0;"></div>
        <div id="scan-time-chart" style="height: 400px; margin: 20px 0;"></div>
        
        <div class="metric-card">
            <h3>🎯 Performance Targets</h3>
            <div id="targets">
                <div class="status-good">✅ Scan Speed: <100μs</div>
                <div class="status-good">✅ Throughput: >1000/s</div>
                <div class="status-good">✅ Profit: >0%</div>
            </div>
        </div>
    </div>
    
    <script>
        // Real-time data updates
        function updateDashboard() {
            fetch('/api/performance')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('scan-speed').textContent = data.avg_scan_time_us + 'μs';
                    document.getElementById('scans-per-sec').textContent = Math.round(data.scans_per_second);
                    document.getElementById('total-profit').textContent = ' + data.total_profit.toFixed(2);
                    document.getElementById('success-rate').textContent = (data.arbitrage_success_rate * 100).toFixed(1) + '%';
                });
        }
        
        setInterval(updateDashboard, 1000); // Update every second
        updateDashboard(); // Initial load
    </script>
</body>
</html>
DASHEOF

echo "✅ Real-time dashboard created"
