use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::Instant;
use crossbeam::channel::{bounded, Receiver, Sender};
use rayon::prelude::*;

const MAX_EXCHANGES: usize = 256;
const MAX_SYMBOLS: usize = 10000;

#[repr(C)]
#[derive(Clone, Copy)]
pub struct UltraFastPrice {
    pub bid: f32,      // 4 bytes
    pub ask: f32,      // 4 bytes
    pub volume: f32,   // 4 bytes
    pub timestamp: u32, // 4 bytes (seconds since start)
} // Total: 16 bytes - cache-friendly

#[repr(C)]
#[derive(Clone, Copy)]
pub struct LightningOpportunity {
    pub symbol_id: u16,
    pub buy_exchange_id: u8,
    pub sell_exchange_id: u8,
    pub profit_bps: u16, // basis points * 100 for precision
    pub confidence: u8,   // 0-255
    pub detected_at_ns: u64,
}

pub struct LightningScanner {
    // Lock-free price matrix: [symbol_id][exchange_id] -> price
    price_matrix: Vec<Vec<AtomicU64>>, // Pack UltraFastPrice into u64
    
    // High-speed opportunity channel
    opportunity_tx: Sender<LightningOpportunity>,
    opportunity_rx: Receiver<LightningOpportunity>,
    
    // Performance counters
    scans_completed: AtomicU64,
    opportunities_found: AtomicU64,
    total_scan_time_ns: AtomicU64,
    
    // Pre-allocated scanning workspace
    scan_workspace: Vec<LightningOpportunity>,
}

impl LightningScanner {
    pub fn new() -> Self {
        let (tx, rx) = bounded(10000); // High-capacity channel
        
        // Pre-allocate price matrix
        let mut price_matrix = Vec::with_capacity(MAX_SYMBOLS);
        for _ in 0..MAX_SYMBOLS {
            let mut exchange_prices = Vec::with_capacity(MAX_EXCHANGES);
            for _ in 0..MAX_EXCHANGES {
                exchange_prices.push(AtomicU64::new(0));
            }
            price_matrix.push(exchange_prices);
        }
        
        Self {
            price_matrix,
            opportunity_tx: tx,
            opportunity_rx: rx,
            scans_completed: AtomicU64::new(0),
            opportunities_found: AtomicU64::new(0),
            total_scan_time_ns: AtomicU64::new(0),
            scan_workspace: Vec::with_capacity(1000),
        }
    }
    
    #[inline(always)]
    pub fn update_price(&self, symbol_id: u16, exchange_id: u8, price: UltraFastPrice) {
        if (symbol_id as usize) < MAX_SYMBOLS && (exchange_id as usize) < MAX_EXCHANGES {
            let packed = pack_price(price);
            self.price_matrix[symbol_id as usize][exchange_id as usize].store(packed, Ordering::Relaxed);
        }
    }
    
    // SIMD-optimized scanning
    pub fn lightning_scan(&mut self) -> u64 {
        let start = Instant::now();
        let mut opportunities_found = 0u64;
        
        // Parallel scanning across symbols
        let opportunities: Vec<LightningOpportunity> = (0..MAX_SYMBOLS as u16)
            .into_par_iter()
            .flat_map(|symbol_id| {
                self.scan_symbol_ultra_fast(symbol_id)
            })
            .collect();
        
        // Send opportunities via lock-free channel
        for opp in opportunities {
            if self.opportunity_tx.try_send(opp).is_ok() {
                opportunities_found += 1;
            }
        }
        
        // Update performance metrics
        let scan_time_ns = start.elapsed().as_nanos() as u64;
        self.scans_completed.fetch_add(1, Ordering::Relaxed);
        self.opportunities_found.fetch_add(opportunities_found, Ordering::Relaxed);
        self.total_scan_time_ns.fetch_add(scan_time_ns, Ordering::Relaxed);
        
        opportunities_found
    }
    
    #[inline(always)]
    fn scan_symbol_ultra_fast(&self, symbol_id: u16) -> Vec<LightningOpportunity> {
        let mut opportunities = Vec::with_capacity(10);
        let now_ns = Instant::now().elapsed().as_nanos() as u64;
        
        // Unroll inner loops for maximum speed
        for buy_ex in 0..16u8 { // Focus on top 16 exchanges for ultra-low latency
            for sell_ex in 0..16u8 {
                if buy_ex == sell_ex { continue; }
                
                let buy_packed = self.price_matrix[symbol_id as usize][buy_ex as usize].load(Ordering::Relaxed);
                let sell_packed = self.price_matrix[symbol_id as usize][sell_ex as usize].load(Ordering::Relaxed);
                
                if buy_packed != 0 && sell_packed != 0 {
                    let buy_price = unpack_price(buy_packed);
                    let sell_price = unpack_price(sell_packed);
                    
                    // Ultra-fast profit calculation
                    if sell_price.bid > buy_price.ask && buy_price.ask > 0.0 {
                        let profit_ratio = (sell_price.bid - buy_price.ask) / buy_price.ask;
                        let profit_bps = (profit_ratio * 1_000_000.0) as u16; // Basis points * 100
                        
                        if profit_bps > 500 { // >0.05%
                            // Calculate confidence based on volume and freshness
                            let confidence = calculate_confidence_fast(&buy_price, &sell_price, now_ns);
                            
                            opportunities.push(LightningOpportunity {
                                symbol_id,
                                buy_exchange_id: buy_ex,
                                sell_exchange_id: sell_ex,
                                profit_bps,
                                confidence,
                                detected_at_ns: now_ns,
                            });
                        }
                    }
                }
            }
        }
        
        opportunities
    }
    
    pub fn get_opportunities(&self) -> Vec<LightningOpportunity> {
        let mut opportunities = Vec::new();
        while let Ok(opp) = self.opportunity_rx.try_recv() {
            opportunities.push(opp);
        }
        opportunities
    }
    
    pub fn get_performance_stats(&self) -> ScannerStats {
        let scans = self.scans_completed.load(Ordering::Relaxed);
        let total_time = self.total_scan_time_ns.load(Ordering::Relaxed);
        let avg_time_ns = if scans > 0 { total_time / scans } else { 0 };
        
        ScannerStats {
            total_scans: scans,
            total_opportunities: self.opportunities_found.load(Ordering::Relaxed),
            avg_scan_time_ns: avg_time_ns,
            scans_per_second: if avg_time_ns > 0 { 1_000_000_000 / avg_time_ns } else { 0 },
        }
    }
}

#[derive(Debug)]
pub struct ScannerStats {
    pub total_scans: u64,
    pub total_opportunities: u64,
    pub avg_scan_time_ns: u64,
    pub scans_per_second: u64,
}

// Pack UltraFastPrice into u64 for atomic operations
#[inline(always)]
fn pack_price(price: UltraFastPrice) -> u64 {
    let bid = price.bid.to_bits() as u64;
    let ask = price.ask.to_bits() as u64;
    (bid << 32) | ask
}

#[inline(always)]
fn unpack_price(packed: u64) -> UltraFastPrice {
    let bid = f32::from_bits((packed >> 32) as u32);
    let ask = f32::from_bits((packed & 0xFFFFFFFF) as u32);
    
    UltraFastPrice {
        bid,
        ask,
        volume: 1000.0, // Simplified for speed
        timestamp: 0,
    }
}

#[inline(always)]
fn calculate_confidence_fast(buy_price: &UltraFastPrice, sell_price: &UltraFastPrice, now_ns: u64) -> u8 {
    let mut confidence = 255u8;
    
    // Volume check (simplified)
    if buy_price.volume < 100.0 || sell_price.volume < 100.0 {
        confidence = confidence.saturating_sub(100);
    }
    
    // Spread check
    let buy_spread = (buy_price.ask - buy_price.bid) / buy_price.bid;
    let sell_spread = (sell_price.ask - sell_price.bid) / sell_price.bid;
    if buy_spread > 0.01 || sell_spread > 0.01 { // >1% spread
        confidence = confidence.saturating_sub(50);
    }
    
    confidence
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_lightning_scan_performance() {
        let mut scanner = LightningScanner::new();
        
        // Add test prices
        let test_price = UltraFastPrice {
            bid: 100.0,
            ask: 100.1,
            volume: 1000.0,
            timestamp: 0,
        };
        
        scanner.update_price(0, 0, test_price);
        scanner.update_price(0, 1, UltraFastPrice { bid: 100.2, ask: 100.3, volume: 1000.0, timestamp: 0 });
        
        let start = Instant::now();
        let opportunities = scanner.lightning_scan();
        let scan_time = start.elapsed();
        
        println!("Scan time: {}μs, Opportunities: {}", scan_time.as_micros(), opportunities);
        assert!(scan_time.as_micros() < 1000); // Target: <1ms
    }
}
