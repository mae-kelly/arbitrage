use std::sync::atomic::{AtomicU64, AtomicF64, Ordering};
use std::time::{Duration, Instant};

pub struct PerformanceMonitor {
    start_time: Instant,
    
    // Counters
    total_scans: AtomicU64,
    total_opportunities: AtomicU64,
    total_flash_loans_found: AtomicU64,
    
    // Timings (nanoseconds)
    total_scan_time_ns: AtomicU64,
    fastest_scan_ns: AtomicU64,
    slowest_scan_ns: AtomicU64,
    
    // Profit tracking
    total_profit_potential: AtomicF64,
    best_opportunity_profit: AtomicF64,
}

impl PerformanceMonitor {
    pub fn new() -> Self {
        Self {
            start_time: Instant::now(),
            total_scans: AtomicU64::new(0),
            total_opportunities: AtomicU64::new(0),
            total_flash_loans_found: AtomicU64::new(0),
            total_scan_time_ns: AtomicU64::new(0),
            fastest_scan_ns: AtomicU64::new(u64::MAX),
            slowest_scan_ns: AtomicU64::new(0),
            total_profit_potential: AtomicF64::new(0.0),
            best_opportunity_profit: AtomicF64::new(0.0),
        }
    }

    pub fn record_scan(&self, scan_time_ns: u64, opportunities_found: u64, profit_potential: f64) {
        self.total_scans.fetch_add(1, Ordering::Relaxed);
        self.total_opportunities.fetch_add(opportunities_found, Ordering::Relaxed);
        self.total_scan_time_ns.fetch_add(scan_time_ns, Ordering::Relaxed);
        
        // Update fastest/slowest times
        self.fastest_scan_ns.fetch_min(scan_time_ns, Ordering::Relaxed);
        self.slowest_scan_ns.fetch_max(scan_time_ns, Ordering::Relaxed);
        
        // Update profit tracking
        self.total_profit_potential.store(
            self.total_profit_potential.load(Ordering::Relaxed) + profit_potential,
            Ordering::Relaxed
        );
        
        if profit_potential > self.best_opportunity_profit.load(Ordering::Relaxed) {
            self.best_opportunity_profit.store(profit_potential, Ordering::Relaxed);
        }
    }

    pub fn record_flash_loan_opportunity(&self, profit: f64) {
        self.total_flash_loans_found.fetch_add(1, Ordering::Relaxed);
        self.total_profit_potential.store(
            self.total_profit_potential.load(Ordering::Relaxed) + profit,
            Ordering::Relaxed
        );
    }

    pub fn get_stats(&self) -> PerfStats {
        let total_scans = self.total_scans.load(Ordering::Relaxed);
        let total_time_ns = self.total_scan_time_ns.load(Ordering::Relaxed);
        let avg_scan_time_ns = if total_scans > 0 { total_time_ns / total_scans } else { 0 };
        
        PerfStats {
            runtime_seconds: self.start_time.elapsed().as_secs(),
            total_scans,
            total_opportunities: self.total_opportunities.load(Ordering::Relaxed),
            total_flash_loans: self.total_flash_loans_found.load(Ordering::Relaxed),
            avg_scan_time_ns,
            fastest_scan_ns: self.fastest_scan_ns.load(Ordering::Relaxed),
            slowest_scan_ns: self.slowest_scan_ns.load(Ordering::Relaxed),
            scans_per_second: if avg_scan_time_ns > 0 { 1_000_000_000 / avg_scan_time_ns } else { 0 },
            total_profit_potential: self.total_profit_potential.load(Ordering::Relaxed),
            best_opportunity: self.best_opportunity_profit.load(Ordering::Relaxed),
        }
    }

    pub fn print_live_stats(&self) {
        let stats = self.get_stats();
        
        println!("🚀 ULTRA-HIGH PERFORMANCE STATS");
        println!("================================");
        println!("⏱️  Runtime: {}s", stats.runtime_seconds);
        println!("🔍 Total scans: {}", stats.total_scans);
        println!("💰 Opportunities found: {}", stats.total_opportunities);
        println!("⚡ Flash loan opportunities: {}", stats.total_flash_loans);
        println!("📊 Avg scan time: {}μs", stats.avg_scan_time_ns / 1000);
        println!("🎯 Fastest scan: {}μs", stats.fastest_scan_ns / 1000);
        println!("🐌 Slowest scan: {}μs", stats.slowest_scan_ns / 1000);
        println!("🔥 Scans per second: {}", stats.scans_per_second);
        println!("💵 Total profit potential: ${:.2}", stats.total_profit_potential);
        println!("🏆 Best opportunity: ${:.2}", stats.best_opportunity);
        
        // Performance targets
        if stats.avg_scan_time_ns < 100_000 {
            println!("✅ SPEED TARGET HIT: <100μs average scan time!");
        }
        if stats.scans_per_second > 1000 {
            println!("✅ THROUGHPUT TARGET HIT: >1000 scans/second!");
        }
    }
}

#[derive(Debug)]
pub struct PerfStats {
    pub runtime_seconds: u64,
    pub total_scans: u64,
    pub total_opportunities: u64,
    pub total_flash_loans: u64,
    pub avg_scan_time_ns: u64,
    pub fastest_scan_ns: u64,
    pub slowest_scan_ns: u64,
    pub scans_per_second: u64,
    pub total_profit_potential: f64,
    pub best_opportunity: f64,
}
